#!/usr/bin/env python#

#A Flight Status Class
#Implements the methods needed to determine flight status such as battery condition, state convergence, distance from home location
#Most function return a boolean indicator partaining to the query requested. 


PKG = 'rospy_tutorials' # this package name
import roslib; roslib.load_manifest(PKG)
import rospy
import numpy
from rospy.numpy_msg import numpy_msg
from Utility import *
import sys
import time
import random
import message_filters
#from message_filters import Subscriber, Cache
from std_msgs.msg import Float64, Bool, Int16
from geometry_msgs.msg import Pose, Point, Quaternion
from rospy.numpy_msg import numpy_msg 

from ListenerClass import ListenerClass


class FlightStatusClass():
    def __init__(self,Publisher,dictionary,queue_size,MinBattVol,safeAltitude,groundlev, throttleThreshold, MaxTime,home,FSM_refreshRate,tolerance):
        print("Initializing Flight Status Object!")
        self.listener               = ListenerClass(queue_size,dictionary)
        self.publisher              = Publisher
        self.minimalBatteryVoltage  = MinBattVol
        self.groundLevel            = groundlev
        self.safeAltitude           = safeAltitude
        self.missionStartTime       = rospy.Time.now().to_sec()
        self.missionMaxTime         = MaxTime
        self.throttleThreshold      = throttleThreshold
        self.homeCoordinates        = home #geometry_msgs/Point
        self.sleepTime              = FSM_refreshRate #When entering states, how long to sleep - slows down the FSM, used for debugging
        self.tolerance              = tolerance
        

    def getMode(self):
        """
        :return: void
        
        Accesor function to publish whether FSM is in Autonomous or Manual MManifold
        """
    def getCurrentPoseStamped(self):
        """
        :return: Current (latest) Stamped Pose msg type
        
        Accesor Function 
        """        
        #print self.listener.poseStampedQueue    
        return self.listener.poseStampedQueue[-1]    
    
    def getCurrentState(self,str_state):
        """
        :param: str_state: string of the state to be returned , either 'x','y','z'
        :return: Current (latest) position attribute, either 'x','y','z'
        
        Accesor Function 
        """
        return getattr(self.getCurrentPoseStamped().pose.position,str_state)    
    
    def getCurrentAltitude(self):
        """
        :return: Current (latest) altitude 'z' 
        
        Accesor Function 
        """        
        return self.getCurrentState('z')
    
    def getMissionDuration(self):
        """
        :return: Mission duration in seconds thus far
        
        Accesor Function for mission duration thus far [seconds]
        """
        return rospy.Time.now().to_sec()-self.missionStartTime
    
    def IsTimeExceeded(self):
        """
        :return: A boolean indicating whether mission duration has exceeded alloted time
        
        Function indicated whether alloted time for mission has be exceeded
        """
        return self.getMissionDuration()>self.missionMaxTime
        
    def ErrorConverge(self,str_attribute):
        """
        :param: str_attribute: string of the state to be returned , either 'x','y','z'
        :return: A boolean indicating whether state has converged 
        
        Utility function to determine if error of controller has converged
        """        
        bool_error   = self.listener.runningStatError[self.listener.dictionary[str_attribute]].Mean()    < 0.1       
        bool_error_d = abs(self.listener.runningStatError_d[self.listener.dictionary[str_attribute]].Mean()-0.01)  < 0       
        if bool_error and bool_error_d :
            print "Error in " ,str_attribute ,"Converged"
            return True
        else :
            print "Error in " ,str_attribute ,"Did not Converge"
            return False

    def ErrorDiverge(self,str_attribute):
        """
        :param: str_attribute: string of the state to be returned , either 'x','y','z'
        :return: A boolean indicating whether state is in the process of diverging 
        
        Utility function to determine if error of controller is divering / unstable
        """        
        #bool_error   = self.listener.runningStatError[self.listener.dictionary[str_attribute]].Mean()    < 1       
        bool_error_d = abs(self.listener.runningStatError_d[self.listener.dictionary[str_attribute]].Mean()-0.01)  > 0       
        if bool_error_d :
            print "Error derivative in " ,str_attribute ,"Diverged"            
            return True
            
        else :
            print "Error derivative in " ,str_attribute ,"Did not Diverge"            
            return False


    def AnyErrorDiverge(self):
        """
        :return: A boolean indicating whether ANY is in the process of diverging 
        
        Utility function to determine if any errors / states are divering / unstable
        """                
        bool = False 
        for str in 'xyz':
            bool *= not self.ErrorDiverge(str)
        return not bool


    def VoltageNeededToGetHome(self):
        """
        :return: A float representing the estimated voltage needed to return home from present location
        
        Utility function computing/estimating the needed voltage to get home from present location
        Can be later implemented as a table lookup [Euclidean Dist, Voltage] or an energy mapping of a trajectory generated by a motion planner called
        """        
        #Presently implements an arbitrary scaling from distance to voltage 
        CurrentStampedPose = self.getCurrentPoseStamped()
        dist = Distance('Euclidean',
                        PoseMsg2NumpyArrayPosition(CurrentStampedPose.pose),
                        PointMsg2NumpyArrayPosition(self.homeCoordinates),
                        3)        
        #print("Vehicle is a distance of %s meters away from home " % dist)
        return 0.1*dist 
        
        
    def IsBatteryOK(self):
        """
        :return: A boolean indicating whether battery status is ok
        
        Function indicating whether battery status is ok (sufficient voltage to continue mission) 
        taking into account minimal safe voltage level,distance from home coordinates and present voltage
        """
        #Compute whether battery level is sufficient based on present voltage level, battery predefined threshold distance to home
##        print ('\n\nCurrent Battery Voltage' , self.listener.batteryVoltage )        
##        print ('Minimal Batt Voltage allowed :' , self.minimalBatteryVoltage )
##        print ('Battery to get HOME:' , self.VoltageNeededToGetHome() )
        if self.listener.batteryVoltage < self.minimalBatteryVoltage + self.VoltageNeededToGetHome() : 
            sys.stdout.write('\rNot Enough Battery...')            
            return False
        else :
            print ('We are good, Enough Battery')
            return True
    
    def window(self,size):
        return numpy.ones(size)/float(size) #Uniform weights
    
   

 