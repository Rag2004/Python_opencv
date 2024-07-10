import socket #connection establishment
import cv2    # type: ignore #Opening Camera & drawing text
import pickle  #serialization of video frames
import struct  #pack the serialized frame length with the frame data for transmission
import imutils  # type: ignore #image processing 
import threading  #for parallel processing
import time
import sys



try:
    vid = cv2.VideoCapture(0)
    if not vid.isOpened():
        try:
            vid = cv2.VideoCapture(1)
            if not vid.isOpened():
                print("Failed to open Camera : ")
        except:
            print("Internal Error")
except:
    print("Error")

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

#roll = input("Enter Name : ")
try:
    roll = sys.argv[1]
except:
    print("oops something went wrong")
    exit()
    
print("Hello, "+roll)
    
if(len(roll) > 14):
    roll = roll[:14]+'..'
message = str(roll)

start_time = time.time()
end_time = start_time + 3
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host_ip = '172.16.97.159'  # Replace with the server's IP address
port = 8000

try:
    client_socket.connect((host_ip, port))      # this is used to establish connection to server for the first time
    encoded_message = message.encode("utf-8")
    client_socket.sendall(encoded_message)
    start_time = time.time()
    end_time = start_time + 3
    Connected = False # it indicate that the client connect to the server
except:
    Connected = True # it indicate that the client fails to connect to the server

def Establish_Connection():
    global Connected  # this indicate the status of connection to the server
    while True:
        if Connected:
            try:
                global client_socket
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((host_ip, port))      #this is used to establish connection to server
                Connected = False

                encoded_message = message.encode("utf-8")
                client_socket.sendall(encoded_message)
                global start_time
                global end_time
                start_time = time.time()
                end_time = start_time + 3
                #print("connected")
            except:
                Connected = True
                #print("Connection Error")
            #print("estab")
        time.sleep(5)
        
        
received_data = "false"

connection_thread = threading.Thread(target=Establish_Connection,)
connection_thread.start()


# to receive acknowledgment data
def receive_text_data():
    global Connected
    while True:
        try:
            # Receive data from the client
            data = client_socket.recv(1024)
            global received_data
            received_data = data.decode()
            print("Received data:", received_data)
            
        except Exception as e:
            Connected = True
            # print("Error receiving data:", str(e))
            # break
        time.sleep(2)


receive_thread = threading.Thread(target=receive_text_data,)
receive_thread.start()


start_none = time.time()
duration = 30     # a variable declared for displaying no user text after 30 sec


def send_data():
    global start_none
    global Connected
    if client_socket:
        while vid.isOpened():
            try:
                img, frame = vid.read()

                # Reduce the frame resolution
                frame = cv2.resize(frame, (640, 480))

                # Convert the image to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Perform face detection using Haar cascade classifier
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

                # Draw rectangles around the detected faces
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

                if time.time() - start_none > duration and len(faces) == 0:
                    cv2.putText(frame, "No User", (200, 50), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                (0, 0, 255), 2, cv2.LINE_AA)
                    
                elif len(faces) > 0:
                    start_none = time.time()

                if received_data == "true" or time.time() < end_time:
                    # Display Text for multiple users
                    if len(faces) > 1:
                        cv2.putText(frame, "Multiple Users", (200, 50), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                    (0, 0, 255), 2, cv2.LINE_AA)

                    # Convert the frame to JPEG format with lower quality (higher compression)
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
                    _, encoded_frame = cv2.imencode(".jpg", frame, encode_param)

                    message = struct.pack("I", len(encoded_frame)) + encoded_frame.tobytes()
                    client_socket.sendall(message)

                    # Send frames at approximately 20 frames per second
                    time.sleep(1/10)
                else:

                    time.sleep(0.5)
            except Exception as e:
                Connected = True
                print(e)
                time.sleep(2)
            
    client_socket.close()

send_thread = threading.Thread(target=send_data,)
send_thread.start()
