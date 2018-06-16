#############################################################################
#                             py-fritz-monitor                              #
#                               Version 1.0.1                               #
#                                                                           #
# The folowing code is written in Python 3                                  #
# It uses port 1012 of fritzbox routers to read incoming and outgoing calls #
# The feature which is used is called call monitor                          #
# If the connection does not work, please read the readme file              #
# Original work by http://www.blog.smartnoob.de                             #
# If you find bugs or you have any question, please inform me via GitHub    #
# https://github.com/HcDevel/py-fritz-monitor                               #
#############################################################################

from call_monitor import callmonitor

#Please read the readme file!

def my_cb (self, id, action, details):
    print ("Call: " + str(id) + " - " + action)
    print (details)
        
call = callmonitor() #Create new instance of py-fritz-monitor, Optinal parameters: host, port
call.register_callback (my_cb) #Defines a function which is called if any change is detected, unset with call.register_callback (-1)
call.connect()

#Some examples, remove in productive usage!
call.parse("09.03.14 21:51:56;CALL;0;12;453423;04829401845;SIP0;") #Simulates outgoing call
call.parse("09.03.14 18:20:59;RING;0;04829401845;453423;SIP0;") #Simmulates incoming call (choose between CALL and RING!)
call.parse("09.03.14 21:52:06;CONNECT;0;12;04829401845;") #Simulates an accepted call
call.parse("09.03.14 21:52:06;DISCONNECT;0;12;04829401845;") #Simulates an ended call

#Please note: Phone numbers are fictional. Don't call them!

input ("Press key to exit\n")
call.disconnect()
