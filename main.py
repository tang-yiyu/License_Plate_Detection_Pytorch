#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 26 15:49:57 2019

@author: xingyu
"""
import sys
sys.path.append('./LPRNet')
sys.path.append('./MTCNN')
from LPRNet_Test import *
from MTCNN import *
import numpy as np
import argparse
import torch
import time
import cv2

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='MTCNN & LPR Demo')
    parser.add_argument("-image_path", help='image path', default='data/2023-04-30-18-44-27/zoom/', type=str)
    parser.add_argument("-save_path", help='save path', default='result/2023-04-30-18-44-27/', type=str)
    parser.add_argument("--scale", dest='scale', help="scale the iamge", default=1, type=int)
    parser.add_argument('--mini_lp', dest='mini_lp', help="Minimum face to be detected", default=(50, 15), type=int)
    args = parser.parse_args()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    lprnet = LPRNet(class_num=len(CHARS), dropout_rate=0)
    lprnet.to(device)
    lprnet.load_state_dict(torch.load('LPRNet/weights/Final_LPRNet_model.pth', map_location=lambda storage, loc: storage))
    lprnet.eval()
    
    STN = STNet()
    STN.to(device)
    STN.load_state_dict(torch.load('LPRNet/weights/Final_STN_model.pth', map_location=lambda storage, loc: storage))
    STN.eval()
    
    print("Successful to build LPR network!")
    

    image_names = os.listdir(args.image_path)
    if not os.path.exists(args.save_path):
        os.makedirs(args.save_path)

    since = time.time()
    for image_name in image_names:
        image = cv2.imread(args.image_path + image_name)
        # image = cv2.resize(image, (0, 0), fx = args.scale, fy = args.scale, interpolation=cv2.INTER_CUBIC)
        bboxes = create_mtcnn_net(image, args.mini_lp, device, p_model_path='MTCNN/weights/pnet_Weights', o_model_path='MTCNN/weights/onet_Weights')
        
        # judge if bboxes is empty
        if bboxes is None:
            print("Can't detect any car!")
            continue
        # print(bboxes)

        for i in range(bboxes.shape[0]):
            
            bbox = bboxes[i, :4]
            x1, y1, x2, y2 = [int(bbox[j]) for j in range(4)]
            if x1 < 0:
                x1 = 0
            if y1 < 0:
                y1 = 0
            if x2 > image.shape[1]:
                x2 = image.shape[1]
            if y2 > image.shape[0]:
                y2 = image.shape[0]
            w = int(x2 - x1 + 1.0)
            h = int(y2 - y1 + 1.0)
            img_box = np.zeros((h, w, 3))
            img_box = image[y1:y2+1, x1:x2+1, :]
            # cv2.imshow('cropped_image', img_box)
            # cv2.imwrite('cropped_image.png', img_box)
            img = cv2.resize(img_box, (94, 24), interpolation=cv2.INTER_CUBIC) # resize cropped image to (94, 24)
            img = (np.transpose(np.float32(img), (2, 0, 1)) - 127.5) * 0.0078125
            img_data = torch.from_numpy(img).float().unsqueeze(0).to(device)
            transfer_img = STN(img_data)
            preds = lprnet(transfer_img)
            preds = preds.cpu().detach().numpy()  # (1, 68, 18)    
            labels, pred_labels = decode(preds, CHARS)
        
            # cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 1)
            # image = cv2ImgAddText(image, labels[0], (x1, y1-12), textColor=(0, 0, 0), textSize=15)
            image = cv2ImgAddText(image, labels[0], bbox)
              
        # image = cv2.resize(image, (0, 0), fx = 1/args.scale, fy = 1/args.scale, interpolation=cv2.INTER_CUBIC)
        cv2.imwrite(args.save_path + image_name, image)
        print("Successful to save image: {}".format(image_name))
        # cv2.imshow('image', image)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        # cv2.imwrite('result.png', image)
    
    print("model inference in {:2.3f} seconds".format((time.time() - since) / len(image_names)))