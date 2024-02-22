# Import libraries
import mujoco as mj
from mujoco.glfw import glfw
import numpy as np
import os
import pandas as pd

# Global variables
flag =0
count=0
xml_path = 'Probing_Physics.xml' #xml file (assumes this is in the same folder as this file)
simend = 100                        #simulation time

# Define the limit for probing
rod_limit = 0.05
positive_force = 1
negative_force = -0.5
force_sensor_limit = 0.24
probe_position_limit = -0.027

Xaxis_position_start=-0.15
probestart=0
onetime=True
Xaxis_position=0

Yaxis_position=0
Yaxis_position_start=0.01
Yflag=0
data_dict = {}
printone=True
onetimeadd=True

# Function to append values to the dictionary
def append_to_dict(data_dict, x_position, y_position, depth,force_value):
   
    if 'Y_Axis' not in data_dict:
        data_dict['Y_Axis'] = []
    if 'depth_mm' not in data_dict:
        data_dict['depth_mm'] = []
    if 'X_Axis' not in data_dict:
        data_dict['X_Axis'] = []
    if 'pressure_N' not in data_dict:
        data_dict['pressure_N'] =[]

    
    data_dict['Y_Axis'].append(y_position)
    data_dict['depth_mm'].append(depth)
    data_dict['X_Axis'].append(x_position)
    data_dict['pressure_N'].append(force_value)
    
# Function to initialize the controller
def init_controller(model,data):
  
    data.ctrl[1]=-0.5
    pass

# Function for controller logic
def controller(model, data):
    global probestart
   
    if probestart==1:
        probe_movement()
    elif probestart==0:
        Horizondal_Xaxis_movement()
    elif probestart==2:
        Bed_movement()

# Function for bed movement
def Bed_movement():
    global count,Yaxis_position_start,probestart,printone,Yflag,onetime,Xaxis_position_start,Yaxis_position
    Yaxis_position=data.qpos[0]

    if count ==50:
        print("Yaxis position",Yaxis_position)
        print("Yaxis position start",Yaxis_position_start)
        count=0
    count+=1


    if Yaxis_position<=Yaxis_position_start and Yflag==0:
        Yaxis_position_start+=0.005
        data.ctrl[2]=0.03
        Yflag=1
        
        
    elif Yaxis_position>Yaxis_position_start and Yflag==1:
        data.ctrl[2]=0
        Yaxis_position_start+=0.005
        probestart=0
        Yflag=0
        data.ctrl[1]=-1
        Xaxis_position_start=-0.15
       
    if Yaxis_position>0.13 and printone:
        df = pd.DataFrame(data_dict)
        print(df)
        df.to_csv('file.csv', index=False)
        printone=False
           

# Function for horizontal X-axis movement
def Horizondal_Xaxis_movement():
    global onetimeadd,count,Xaxis_position_start,probestart,flag,onetime,Xaxis_position
    
    Xaxis_position=data.qpos[1]

    if count ==50:
        print("Xaxis position",Xaxis_position)
        print("Xaxis position start",Xaxis_position_start)
        count=0
    count+=1

    if Xaxis_position>Xaxis_position_start and flag==0:
        flag=0

    elif Xaxis_position<Xaxis_position_start and flag==0:
        data.ctrl[1]=0.5
        flag=1
        Xaxis_position_start+=0.01
        
    elif Xaxis_position>Xaxis_position_start and flag==1:
        data.ctrl[1]=0
        Xaxis_position_start+=0.01
        probestart=1
        flag=0
        onetime=True
        onetimeadd=True

    if Xaxis_position>0.15:
        probestart=2
 
# Function for probe movement
def probe_movement():
    force_sensor_value = data.sensordata[0]
    probing_position_value=data.qpos[2]
    global onetimeadd,count,probe_position_limit,probestart,onetime,Xaxis_position,Yaxis_position

    if count ==50:
        print("Force",force_sensor_value)
        print("Horizondal Position",probing_position_value)
        count=0
    count+=1
    
    if onetime:
       data.ctrl[0]= positive_force
       onetime=False 

    if force_sensor_value > force_sensor_limit  :
        print("Force sensor value exceeded the limit!")
        data.ctrl[0]= negative_force
        if onetimeadd:
            append_to_dict(data_dict,Xaxis_position,Yaxis_position, probing_position_value,force_sensor_value)
            onetimeadd=False
    elif probing_position_value<probe_position_limit:
        data.ctrl[0]= 0
        probestart=0
        print("velocity0",data.ctrl[0])

#get the full path to XML file
dirname = os.path.dirname(__file__)
abspath = os.path.join(dirname + "/" + xml_path)
xml_path = abspath

# MuJoCo data structures
model = mj.MjModel.from_xml_path(xml_path)  # MuJoCo model
data = mj.MjData(model)                     # MuJoCo data
cam = mj.MjvCamera()                        # Abstract camera
opt = mj.MjvOption()                        # visualization options

# Init GLFW, create window, make OpenGL context current, request v-sync
glfw.init()
window = glfw.create_window(1200, 900, "Demo", None, None)
glfw.make_context_current(window)
glfw.swap_interval(1)

# initialize visualization data structures
mj.mjv_defaultCamera(cam)
mj.mjv_defaultOption(opt)
scene = mj.MjvScene(model, maxgeom=10000)
context = mj.MjrContext(model, mj.mjtFontScale.mjFONTSCALE_150.value)



# Example on how to set camera configuration
cam.azimuth = 90
cam.elevation = -40
cam.distance = 1.3
cam.lookat = np.array([0.0, 0.0, 0])

#initialize the controller
init_controller(model,data)

#set the controller
mj.set_mjcb_control(controller)

while not glfw.window_should_close(window):
    time_prev = data.time

    while (data.time - time_prev < 1.0/60.0):
        mj.mj_step(model, data)

    if (data.time>=simend):
        break;

    # get framebuffer viewport
    viewport_width, viewport_height = glfw.get_framebuffer_size(
        window)
    viewport = mj.MjrRect(0, 0, viewport_width, viewport_height)


    # Update scene and render
    mj.mjv_updateScene(model, data, opt, None, cam,
                       mj.mjtCatBit.mjCAT_ALL.value, scene)
    mj.mjr_render(viewport, scene, context)

    # swap OpenGL buffers (blocking call due to v-sync)
    glfw.swap_buffers(window)

    # process pending GUI events, call GLFW callbacks
    glfw.poll_events()
    
# Terminate GLFW
glfw.terminate()
