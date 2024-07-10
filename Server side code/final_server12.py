import socket
import cv2 # type: ignore
import pickle
import struct
import threading
import concurrent.futures    
import numpy as np # type: ignore
import time
import win32api  # type: ignore #To Modify Cursor From + to arrow here
import win32con  # type: ignore #To Modify Cursor From + to arrow here 
import datetime


# Define the arrow cursor ID
arrow_cursor_id = win32con.IDC_ARROW

# Constants for server configuration
# SERVER_HOST = '172.16.97.149'  # Update the desired IP address here
SERVER_HOST = '172.16.148.60'
print(SERVER_HOST)

SERVER_PORT = 8000   #this port number should be same AS OF CLIENT SIDE AND SERVER SIDE
MIN_FRAME_WIDTH = 120
MIN_FRAME_HEIGHT = 90
MAX_FRAME_WIDTH = 720
MAX_FRAME_HEIGHT = 2400

FONT_SCALE = 0.7
FONT_THICKNESS = 2

MARGIN = 10
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 40
TEXT_MARGIN = 5
TEXT_COLOR = (0, 0, 0)  # Black text color for IP address and client name

CLIENT_INFO_WIDTH = BUTTON_WIDTH + 2 * MARGIN

start = 0       #starting ip index for displaying ip address
number_of_ip_display = 10 #set the number of ips to display
number_of_ip_slide = 2 #slide ips

video_start = 0  # for displaying videos
number_of_video_display = 9 # set the number of video to display
number_of_video_slide = 3 #slide 3 videos at time 
           

# Dictionary to store client frames and connection status
client_frames = {}          #for displaying live video using frames
client_frame1 = {}          # for displaying frames on main display
client_status = {}          # for checking connection status

client_names = {}    # for getting names from clients

lock = threading.Lock()     #when it's deleting/Inserting frames automaically, it will lock this process, so other processes doesn't run and don't give error
current_client = ""         #getting current client socket to display video in full window

pixel = 1
#sleep_time = 3

#For generating log file
def logAction(user,ip,status):
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    mylog = f'[{formatted_time}] User {user} with IP ({ip}) Status:{status}\n'
    file = open("access_log.txt", "a")
    file.write(mylog)
    file.close()

#For receiving name of user when connected
def getSocketName(client_socket):
    global client_names
    try:
        received_data = client_socket.recv(1024)
        roll = received_data.decode("utf-8")
        client_names[client_socket] = roll
        logAction(roll,client_socket.getpeername()[0],"Connected")  #0 for IP address and 1 for Port Number
        print("Socket for ",roll," has created")
    except:
        print("getSocketNameError")
    #print(allClients[roll])


def handle_client(client_socket):
    # Variables for receiving data
    data = b""
    payload_size = struct.calcsize("I")

    # Set time for receiving data only for 3 sec when the client is connected
    start_time = time.time()
    end_time = start_time + 3

    # For receiving data for 3 sec when the client is connected or for the current selected client
    while True:
        try:
            while len(data) < payload_size:
                packet = client_socket.recv(4 * 1024)
                if not packet:
                    break
                data += packet

            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("I", packed_msg_size)[0]

            while len(data) < msg_size:
                data += client_socket.recv(4 * 1024)
            frame_data = data[:msg_size]
            data = data[msg_size:]

            # Decode the JPEG frame back to the original frame
            frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)

            # Store the frame in the dictionary based on the client socket
            with lock:
                if client_socket not in client_frame1.keys():
                    client_frame1[client_socket] = frame
                    print(frame)

                client_frames[client_socket] = frame
                client_status[client_socket] = True

            if current_client == client_socket or time.time() < end_time:
                sleep = 0
            else:
                sleep = 3
            time.sleep(sleep)

        except Exception as e:
            logAction(client_names[client_socket], client_socket.getpeername()[0], "Disconnected")
            print(f"Error receiving frame from {client_socket.getpeername()}: {str(e)}")
            with lock:
                if client_socket in client_frames:
                    del client_frames[client_socket]
                    del client_status[client_socket]
                    del client_frame1[client_socket]
            break
           
first_window = True
def button_callback(event, x, y, flags, param):
    global first_window
    global curr_index
    buttons = param
    if event == cv2.EVENT_MOUSEMOVE:
            # Change the cursor to an arrow
            win32api.SetCursor(win32api.LoadCursor(0, arrow_cursor_id))

    if event == cv2.EVENT_LBUTTONDOWN:
        global display_participants
        global display_participants_full
        win32api.SetCursor(win32api.LoadCursor(0, arrow_cursor_id))
        for button in buttons:
            min_x,max_x,min_y,max_y,port,curr_index = button

            if min_x <= x <= max_x and min_y <= y <= max_y:            
                global start   #for ip address
                global video_start    #for video displaying

                if(port == "DOWN"):
                    start+=number_of_ip_slide

                elif(port == "UP"):
                    start-=number_of_ip_slide

                elif(port == "RIGHT"):
                    video_start += number_of_video_slide

                elif(port == "LEFT"):
                    video_start -= number_of_video_slide

                elif (port == "PARTICIPANT"):
                    if display_participants:
                        display_participants = False
                    else:
                        display_participants = True

                elif (port == "PARTICIPANT_FULL"):
                    if display_participants_full:
                        display_participants_full = False
                    else:
                        display_participants_full = True

                else:                    
                    global current_client                 
                    if(not first_window):
                        send_text_data(current_client,"false")
                    client_socket, frame = list(client_frames.items())[curr_index]
                    send_text_data(client_socket,"true")

                    global pixel
                    pixel = 4*1024
                    current_client = client_socket
                    
                    if(first_window):
                        display_thread = threading.Thread(target=display)
                        display_thread.start()
                        first_window = False
                break

global video_number
video_number = 1

def record_call(event, x, y, flags, param): 
    global recording
    global fourcc
    global out
    global st
    win32api.SetCursor(win32api.LoadCursor(0, arrow_cursor_id))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Specify the video codec
    global video_number
    if event == cv2.EVENT_LBUTTONDOWN:
        min_x,min_y,max_x,max_y,recording = param
        if(x >= min_x and x <= max_x and y >= min_y and y <= max_y):
            if recording:
                recording = False
                #print(time.time()-st)
                out.release()
            else:
                name = str(video_number)+'.mp4'
                #st=time.time()
                out = cv2.VideoWriter(name, fourcc, 57, (900, 900))  # Set the output file name, codec, FPS, and frame size
                recording = True
                video_number+=1


def display(): 
    # Create a named window with a window name and title bar
    cv2.namedWindow("Client Window",cv2.WINDOW_NORMAL)

    frame_width = 900
    frame_height = 900
    #for video saving
    frame_count = 1
    
    #creating record button
    global recording
    recording = False
    record_button_size = (45, 45)
    record_button_text = "Record"
    record_button_position = (int(frame_width - record_button_size[0]-5), frame_height - record_button_size[0]-5)

    while True:
        try:
            with lock:  
                # Calculate the optimal frame size based on the number of clients
                rows = 1
                cols = 1
                client_socket, frame = list(client_frames.items())[curr_index]
                
                # Create an empty screen to display the frame
                screen = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
                # Resize the frame to match the screen dimensions
                frame = cv2.resize(frame, (frame_width, frame_height))
                
                # Add a border to the frame
                frame_with_border = cv2.copyMakeBorder(frame, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(255, 0, 0))

                # Get the client's IP address
                client_name = client_names[client_socket]
                text = f"{client_name}"
                cv2.putText(frame_with_border, text, (5, frame_height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

                # Display the frame on the screen
                screen = frame_with_border
                #recording video annd displaying start and stop text
                if recording:          
                    pause_image = cv2.imread('pause.jpg')
                    print("yes")
                    pause_image = cv2.resize(pause_image, (record_button_size[1], record_button_size[0]))
                    screen[record_button_position[0] : record_button_position[0] + record_button_size[0], record_button_position[1] : record_button_position[1] + record_button_size[1]] = pause_image
                    print("yes")
                    #recording video
                    if(frame_count % 50 < 20):
                        blink_image = cv2.imread('dot.png')
                        blink_image = cv2.resize(blink_image, (record_button_size[1]//2, record_button_size[0]//2))
                        screen[record_button_position[0] + record_button_size[0]//4: record_button_position[0] + (record_button_size[0] // 2 + record_button_size[0] // 4), record_button_position[1]  - record_button_size[1]//2 - 5  : record_button_position[1]-5] = blink_image
                   
                    out.write(frame)
                    frame_count+=1

                else:
                    print("no")
                    play_image = cv2.imread('play.png')
                    play_image = cv2.resize(play_image, (record_button_size[1], record_button_size[0]))
                    screen[record_button_position[0] : record_button_position[0] + record_button_size[0], record_button_position[1] : record_button_position[1] + record_button_size[1]] = play_image
                    print("no")
                button = [record_button_position[0],
                          record_button_position[1],
                          record_button_position[0] + record_button_size[0],
                          record_button_position[1] + record_button_size[1],
                          recording]
                cv2.setMouseCallback("Client Window", record_call , button)
                
                # Display the frame
                cv2.imshow('Client Window', screen)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    send_text_data(client_socket,"false")
                    break
                
        except Exception as e:
            # Check for key press to exit
            print("DIsplay : ", e)
            break

    global pixel
    pixel = 1
    
    global first_window
    first_window = True

    try:
        # Keep the window open untill close button is pressed
        cv2.destroyWindow('Client Window')
        out.release()
    except:
        print("ERROR")
        
#Sending message to client
def send_text_data(client_socket, text):
    try:
        # Send data to the server
        client_socket.sendall(text.encode())
        print("Text data sent:", text)
        
    except Exception as e:
        print("Error sending data:", str(e))

# Function to display frames from all clients
def display_frames():
    # Create a named window with a window name and title bar
    cv2.namedWindow('Video Streaming', cv2.WINDOW_NORMAL)
    cv2.setWindowTitle('Video Streaming', 'Video Streaming from Clients')

    global display_participants     #Display and hide names of users
    display_participants = True

    global display_participants_full #display and hide window of participants name
    display_participants_full = False
   
    while True:
        with lock:
            num_clients = len(client_frames)
            if num_clients == 0:
                time.sleep(0.5)
                continue

            # Collect the frames and associated IP addresses
            frames = []
            ips = []
            for client_socket, frame in client_frame1.items():
                frames.append(frame)
                ips.append(client_socket)  # Get the IP address and port of the client socket

            # Calculate the optimal frame size based on the number of clients
            rows = int(np.ceil(np.sqrt(min(number_of_video_display, num_clients - video_start))))
            cols = int(np.ceil(min(number_of_video_display, num_clients - video_start) / rows))
            frame_width = min(max(int(1280 / cols), MIN_FRAME_WIDTH), MAX_FRAME_WIDTH)
            frame_height = min(max(int(720 / rows), MIN_FRAME_HEIGHT), MAX_FRAME_HEIGHT)

            if display_participants_full:
                screen_width = cols * frame_width + CLIENT_INFO_WIDTH + 2 * MARGIN
            else:
                 screen_width = cols * frame_width +5  
            screen_height = rows * frame_height + 2 * MARGIN

            # Create an empty screen to display the frames
            screen = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)

            if(display_participants_full):
                screen[:, -CLIENT_INFO_WIDTH - (2*MARGIN) + 5:] = (255, 255, 255)  # Set the background color to white

            max_text_width = 0
            max_text_height = 0
            buttons = []    #for getting position of buttons or ip address to be clickable

            for ip in ips:
                client_name = client_names[ip]
                ip_text = f"{client_name}"
                text_width, text_height = cv2.getTextSize(ip_text, cv2.FONT_HERSHEY_COMPLEX, 0.5, 1)[0]
                max_text_width = max(max_text_width, text_width)
                max_text_height = max(max_text_height, text_height)

            left_margin = max_text_width + TEXT_MARGIN
            if display_participants_full:
                #Display Participants Text
                button_x = screen_width - CLIENT_INFO_WIDTH + MARGIN    # for displaying participant button in sidebar
                t_width, t_height = cv2.getTextSize("Participants", cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]     
                
                cv2.putText(screen, f"Participants: {num_clients}", (button_x + BUTTON_WIDTH//20 , 10 + TEXT_MARGIN + max_text_height),
                                cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, (0,0,0), FONT_THICKNESS, cv2.LINE_AA)

                buttons.append((button_x + BUTTON_WIDTH // 20, button_x + t_width + BUTTON_WIDTH//5,
                                10, 10 + t_height,"PARTICIPANT",-1))  #x_start,x_end,y_start,y_end
            

            if display_participants and display_participants_full:
                is_first = True #for checking if first time drawing up arrow
                global start
                if(start >= len(ips)):
                    start = max(start - number_of_ip_display,0)
                end = start+number_of_ip_display

                for i in range(start,min(end,len(ips))): 
                    button_x = screen_width - CLIENT_INFO_WIDTH - 15
                    # if down arrow is pressed one or more time

                    if start > 0:
                        up_image = cv2.imread('up.png')
                        #display up arrow
                        if is_first:
                            button_y = MARGIN + (BUTTON_HEIGHT + max_text_height-20) * (i+1-start)
                           
                            up_image = cv2.resize(up_image, (BUTTON_WIDTH-80, BUTTON_HEIGHT+20))
                            screen[button_y : button_y + BUTTON_HEIGHT+20, button_x+40 : button_x + BUTTON_WIDTH-40] = up_image
                            
                            buttons.append((button_x+40, button_x + BUTTON_WIDTH-40, button_y, button_y + BUTTON_HEIGHT+20,
                                            "UP",i))
                            is_first = False
                    
                    # display ip address
                    if(is_first == False):
                        button_y = MARGIN+35 + (BUTTON_HEIGHT + max_text_height-20) * (i+2-start)
                    else:
                        button_y = MARGIN+30 + (BUTTON_HEIGHT-10) * (i+1-start)

                    ip_text = f"{client_names[ips[i]]}"    
                    cv2.putText(screen, ip_text, (button_x+4, button_y + max_text_height),
                                cv2.FONT_HERSHEY_COMPLEX, 0.6, (255,0,0), 1, cv2.LINE_AA)
   
                    buttons.append((button_x, button_x + max_text_width, button_y  , button_y + +
                                    (2*max_text_height), ip,i))

                    #to display down arrow
                    if(i==end-1 and end < len(ips)):
                        down_image = cv2.imread('down.png')

                        #checking if up arrow is included or not
                        if(is_first == False):
                            button_y = MARGIN + (BUTTON_HEIGHT + max_text_height-5) * (i+2-start)

                        else:
                            button_y = MARGIN + (BUTTON_HEIGHT + max_text_height) * (i+1-start)                       

                        down_image = cv2.resize(down_image, (BUTTON_WIDTH-80, BUTTON_HEIGHT+20))
                        screen[button_y : button_y + BUTTON_HEIGHT+20, button_x+40 : button_x + BUTTON_WIDTH-40] = down_image
                        

                        buttons.append((button_x+40, button_x + BUTTON_WIDTH-40, button_y, button_y + BUTTON_HEIGHT +20,
                                        "DOWN",i))
                    
            is_first_left = True #for printing up left button single time

            #checking for video start for client, must be less than total clients
            if(video_start >= num_clients):
                start = max(start - number_of_ip_display,0)
            video_end = video_start + number_of_video_display

            # Iterate through the frames of all connected clients
            for i, (client_socket, frame) in enumerate(client_frame1.items()):
                #print(frame)
                if( i >= video_start and i < video_end):
                    
                    # Calculate the position to display the frame on the screen
                    row = (i-video_start) // cols
                    col = (i-video_start) % cols
                    x = col * frame_width
                    y = row * frame_height
                    margin = 0      #give margin for displaying number of clients

                    #displaying total number of clients 
                    if(row == 0):
                        margin=50
                        text = f"Participants: {num_clients}"
                        button_y = 0
                        
                        if display_participants_full:
                            button_x = (screen_width - CLIENT_INFO_WIDTH - MARGIN) //2 - (BUTTON_WIDTH//2)
                        else:
                            button_x = (screen_width - CLIENT_INFO_WIDTH - MARGIN) //2

                        cv2.rectangle(screen, (button_x, button_y), (button_x + BUTTON_WIDTH, button_y + BUTTON_HEIGHT),
                              (200, 200, 200), cv2.FILLED)
                        cv2.putText(screen, text, (button_x  + TEXT_MARGIN, button_y + TEXT_MARGIN + max_text_height),
                            cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, (40,20,219), FONT_THICKNESS, cv2.LINE_AA)
                    
                        buttons.append((button_x , button_x + BUTTON_WIDTH ,
                                button_y, button_y + BUTTON_HEIGHT,"PARTICIPANT_FULL",-2))
                    
                    # Resize the frame to match the partition size
                    frame = cv2.resize(frame, (frame_width-4, frame_height-margin-4))

                    # Add a border to the frame
                    frame_with_border = cv2.copyMakeBorder(frame, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(0, 0, 255))

                    # Get the client's IP address
                    client_address = client_socket.getpeername()[0]

                    # Add the IP address text to the frame
                    text = f"{client_names[client_socket]}"
                    if(row == 0):
                        cv2.putText(frame_with_border, text, (10, frame_height - 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    else:
                        cv2.putText(frame_with_border, text, (10, frame_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    # Adjust frame size to match the screen dimensions
                    frame_with_border = frame_with_border[:frame_height, :frame_width]

                    # Display the frame from the matrices of image
                    screen[y+margin:y  + frame_height, x :x + frame_width] = frame_with_border
                elif(i > video_end):
                    break

                # if right arrow is pressed one or more time
                if (video_start > 0 and (i == video_end-1 or i == num_clients-1)):

                    #display left arrow
                    if is_first_left:
                        button_x = 0
                        button_y = screen_height//2 - (BUTTON_WIDTH//2)

                        cv2.rectangle(screen, (button_x, button_y), (button_x + 18, button_y + BUTTON_WIDTH),
                              (200, 200, 200), cv2.FILLED)
                        cv2.putText(screen, "<", (button_x + 2 , button_y + BUTTON_WIDTH//2 - TEXT_MARGIN + max_text_height),
                            cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, (255,0,0), FONT_THICKNESS, cv2.LINE_AA)

                        buttons.append((button_x, button_x + 18, button_y, button_y + BUTTON_WIDTH, "LEFT",i))
                        is_first_left = False
 
                #to display right arrow
                if(i==video_end-1 and video_end < num_clients):

                    if display_participants_full:
                        button_x =  screen_width - CLIENT_INFO_WIDTH - MARGIN - BUTTON_HEIGHT
                    else:
                        button_x = screen_width - BUTTON_HEIGHT +10
                    button_y = screen_height//2 - (BUTTON_WIDTH//2)

                    cv2.rectangle(screen, (button_x, button_y), (button_x + BUTTON_HEIGHT - MARGIN, button_y + BUTTON_WIDTH),
                              (200, 200, 200), cv2.FILLED)

                    cv2.putText(screen, ">", (button_x + TEXT_MARGIN, button_y + BUTTON_WIDTH//2 - TEXT_MARGIN + max_text_height),
                            cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, (255,0,0), FONT_THICKNESS, cv2.LINE_AA)

                    buttons.append((button_x, button_x + BUTTON_HEIGHT - MARGIN, button_y,
                                    button_y + BUTTON_WIDTH, "RIGHT",i))

            cv2.setMouseCallback("Video Streaming", button_callback, buttons)
            # Display the combined frames on the screen
            cv2.imshow('Video Streaming', screen)

            # Check for  key press to exit
            if cv2.waitKey(1) & 0xFF == 27:
                break
        time.sleep(.1)
        
    # Close the OpenCV windows
    cv2.destroyAllWindows()

# Create a server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((SERVER_HOST, SERVER_PORT))
server_socket.listen(150)  # Allow 150 clients to connect simultaneously

# Start a thread to display frames from all clients
display_thread = threading.Thread(target=display_frames)
display_thread.start()

# Create a thread pool executor with a maximum of 150 threads
executor = concurrent.futures.ThreadPoolExecutor(max_workers=150)

while True:
    # Accept a client connection
    client_socket, client_address = server_socket.accept()
    #print(client_socket)
    getSocketName(client_socket)
  # Start a new thread to handle the client connection
    executor.submit(handle_client, client_socket)   

            
           
