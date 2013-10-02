#Listener class object
#!/usr/bin/env python#

PKG = 'fsm' # this package name
import roslib; roslib.load_manifest(PKG)
import rospy
import numpy
import time
import message_filters
#from message_filters import Subscriber, Cache
from std_msgs.msg import Float64, Bool, Int16
from geometry_msgs.msg import Pose, Point, Quaternion, PoseStamped
from quadrotor_msgs.msg import RadioControl, BatteryStatus, ControllerError
from rospy.numpy_msg import numpy_msg 
from Utility import *
from RunningStatClass import RunningStatClass 
import collections  

class ListenerClass():
    def __init__(self,queue_size,dictionary):
        print("Initializing Listener Object!")
        #Define Dictionary 
        self.dictionary       = dictionary
        #Define topics to which the listener should subscribe (should be imported from a parameter server later)
        self.StartedListening = rospy.Time.now()
        batteryVoltage_topic  = 'battery'
        poseStamped_topic     = 'poseStamped'
        ControllerError_topic = 'ControllerError'
        RadioControl_topic    = 'RadioControl'
        #Create subscribers to those topics (msg_type should also be loaded from server)
        print("Starting to Listen!")
        self.subscriber_RadioControl   = rospy.Subscriber(RadioControl_topic,
                                                          RadioControl,
                                                          self.RadioControl_callback)        
        self.subscriber_batteryVoltage = rospy.Subscriber(batteryVoltage_topic,
                                                          BatteryStatus,
                                                          self.battery_callback)        
        self.subscriber_ControllerError= rospy.Subscriber(ControllerError_topic,
                                                          ControllerError,
                                                          self.ControllerError_callback)        
        self.subscriber_pose           = rospy.Subscriber(poseStamped_topic,
                                                          PoseStamped,
                                                          self.poseStamped_callback)       
        #self.pose_cache = message_filters.Cache(self.subscriber_pose, 100)
        #self.pose_cache.registerCallback(self.pose_callback)
        #Initialize the data loggers for the listener 
        self.batteryVoltage     = 15
        self.poseStampedQueue   = collections.deque([],queue_size)
        self.ctrlThrottle       = 0
        self.AutoPilotSwitch    = True
        self.MissionGoSwitch    = True
        self.runningStatPose    = [RunningStatClass('x',queue_size),
                                  RunningStatClass('y',queue_size),
                                  RunningStatClass('z',queue_size)]
        self.runningStatError   = [RunningStatClass('error_x',queue_size),
                                   RunningStatClass('error_y',queue_size),
                                   RunningStatClass('error_z',queue_size)]
        self.runningStatError_d = [RunningStatClass('d_error_x',queue_size),
                                   RunningStatClass('d_error_y',queue_size),
                                   RunningStatClass('d_error_z',queue_size)]
        

    def RadioControl_callback(self,data):
        #rospy.loginfo(rospy.get_caller_id() + " I heard  %s  ",  data)
        self.ctrlThrottle     = data.throttle
        self.AutoPilotSwitch  = data.flap >= 0
        self.MissionGoSwitch  = data.flap == -1
        
        
    def battery_callback(self,data):
        #rospy.loginfo(rospy.get_caller_id() + " I heard  %s  ",  data.data)
        self.batteryVoltage  = data.voltage
        
    def poseStamped_callback(self,data):
        #rospy.loginfo(rospy.get_caller_id() + " I heard  %s  ",  data)
        self.runningStatPose[self.dictionary['x']].push(data.pose.position.x)        
        self.runningStatPose[self.dictionary['y']].push(data.pose.position.y)
        self.runningStatPose[self.dictionary['z']].push(data.pose.position.z)
        self.poseStampedQueue.append(data) #Append the latest msg to the deque, column-wise
               
    def ControllerError_callback(self,data):
        #rospy.loginfo(rospy.get_caller_id() + " I heard  %s  ",  data)

        #Error , e.g. :(z_ref-z)
        self.runningStatError[self.dictionary['x']].push(abs(data.error.x))
        self.runningStatError[self.dictionary['y']].push(abs(data.error.y))
        self.runningStatError[self.dictionary['z']].push(abs(data.error.z))
        
        #Derivative of Error  , e.g. :(d/dt)(z_ref-z) or (velocity_des-velocity)
        self.runningStatError_d[self.dictionary['x']].push(data.error_d.x)
        self.runningStatError_d[self.dictionary['y']].push(data.error_d.y)
        self.runningStatError_d[self.dictionary['z']].push(data.error_d.z)
    