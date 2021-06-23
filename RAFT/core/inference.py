import os
import sys
sys.path.append('RAFT/core')

from argparse import ArgumentParser
from collections import OrderedDict

import cv2
import numpy as np
import torch

from raft import RAFT
from utils import flow_viz


def frame_preprocess(frame, device):
    frame = torch.from_numpy(frame).permute(2, 0, 1).float()
    frame = frame.unsqueeze(0)
    frame = frame.to(device)
    return frame


def vizualize_flow(img, flo, save, counter):
    # permute the channels and change device is necessary
    img = img[0].permute(1, 2, 0).cpu().numpy()
    flo = flo[0].permute(1, 2, 0).cpu().numpy()

    # map flow to rgb image
    flo = flow_viz.flow_to_image(flo)
    flo = cv2.cvtColor(flo, cv2.COLOR_RGB2BGR)

    # concatenate, save and show images
    img_flo = np.concatenate([img, flo], axis=0)
    if save:
        cv2.imwrite(f"demo_frames/frame_{str(counter)}.jpg", img_flo)
    cv2.imshow("Optical Flow", img_flo / 255.0)
    k = cv2.waitKey(25) & 0xFF
    if k == 27:
        return False
    return True


def get_cpu_model(model):
    new_model = OrderedDict()
    # get all layer's names from model
    for name in model:
        # create new name and update new model
        new_name = name[7:]
        new_model[new_name] = model[name]
    return new_model


def inference(args):
    # get the RAFT model
    model = RAFT(args)
    # load pretrained weights
    pretrained_weights = torch.load(args.model ,map_location ='cpu')

    save = args.save
    if save:
        if not os.path.exists("demo_frames"):
            os.mkdir("demo_frames")

    if torch.cuda.is_available():
        device = "cuda"
        # parallel between available GPUs
        model = torch.nn.DataParallel(model)
        # load the pretrained weights into model
        model.load_state_dict(pretrained_weights)
        model.to(device)
    else:
        device = "cpu"
        # change key names for CPU runtime
        pretrained_weights = get_cpu_model(pretrained_weights)
        # load the pretrained weights into model
        model.load_state_dict(pretrained_weights)

    # change model's mode to evaluation
    model.eval()

    size = (250,250)
    video_path = args.videoframepath
    frame_list = os.listdir(video_path)
    frame_list.sort()
    frame_path_list = []
    for frame in frame_list:
        frame_path = os.path.join(video_path+'/'+frame)
        frame_path_list.append(frame_path)
    
    # for frame_path in frame_path_list:
    #     print(frame_path)
    

    # generating outputpath
    ls = video_path.split('/')[:-1]
    ls.append('flow')
    outputPath = '/'
    outputPath = outputPath.join(ls)
    


    # capture the video and get the first frame
    # cap = cv2.VideoCapture(video_path)
    # ret, frame_1 = cap.read()
    frame_1 = cv2.imread(frame_path_list[0])
    
    # frame preprocessing
    #print(frame_1.shape)
    
    frame_1 = frame_preprocess(frame_1, device)
    
    # print(frame_1.shape)
    #############
    # fourcc = cv2.VideoWriter_fourcc(*'XVID')
    # size = (640,360)
    # fps = 30
    # out = cv2.VideoWriter('opticalflow.avi',cv2.VideoWriter_fourcc('M','J','P','G'),fps,size)

    count = 0
    #############
    index = 1
    counter = 0
    with torch.no_grad():
        while True:
            # read the next frame
            frame_2 = cv2.imread(frame_path_list[index])
            index+=1
            if(index >= len(frame_path_list)):
                break
            # if not ret:
            #     break
            # preprocessing
            frame_2 = frame_preprocess(frame_2, device)
            # predict the flow
            flow_low, flow_up = model(frame_1, frame_2, iters=args.iters, test_mode=True)
            # transpose the flow output and convert it into numpy array
            
            ###############################
            flo = flow_up  

            flo = flo[0].permute(1, 2, 0).cpu().numpy()
            flo = flow_viz.flow_to_image(flo)
            flo = cv2.cvtColor(flo, cv2.COLOR_RGB2BGR)
            flo = cv2.resize(flo,size)
            if count == 0:
                paddedCount = '0000'
            else:
                paddedCount = '%04d' % count
            cv2.imwrite(
                outputPath+ '/' + paddedCount +'.jpg',flo
            )
            count+=1
            # out.write(flo)
            ###################################


            ### UNCOMMENT FOR VISUALIZATION
            # ret = vizualize_flow(frame_1, flow_up, save, counter)
            # if not ret:
            #     break
            frame_1 = frame_2
            counter += 1

    #out.release()





def main():
    parser = ArgumentParser()
    parser.add_argument("--model", help="restore checkpoint")
    parser.add_argument("--iters", type=int, default=12)
    parser.add_argument("--videoframepath", type=str, default="./videos/car.mp4")
    parser.add_argument("--save", action="store_true", help="save demo frames")
    parser.add_argument("--small", action="store_true", help="use small model")
    parser.add_argument(
        "--mixed_precision", action="store_true", help="use mixed precision"
    )

    args = parser.parse_args()
    

    # print(args.model)
    # print(type(args))
    inference(args)


if __name__ == "__main__":
    main()
