#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 26 15:49:57 2019

@author: xingyu
"""
import sys
import os
sys.path.append(os.getcwd())
from PIL import Image, ImageDraw, ImageFont
from model.LPRNET import LPRNet, CHARS
from model.STN import STNet
import numpy as np
import argparse
import torch
import time
import cv2

def convert_image(inp):
    # convert a Tensor to numpy image
    inp = inp.squeeze(0).cpu()
    inp = inp.detach().numpy().transpose((1,2,0))
    inp = 127.5 + inp/0.0078125
    inp = inp.astype('uint8') 

    return inp

def cv2ImgAddText(img, text, pos, textColor=(255, 0, 0), textSize=12):
    if (isinstance(img, np.ndarray)):  # detect opencv format or not
        img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)
    fontText = ImageFont.truetype("LPRNet/data/NotoSansCJK-Regular.ttc", textSize, encoding="utf-8") # use in main.py
    # fontText = ImageFont.truetype("data/NotoSansCJK-Regular.ttc", textSize, encoding="utf-8") # use in LPRNet_Test.py
    draw.text(pos, text, textColor, font=fontText)

    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)

"""
@ brief: draw the box and text on the image
@ param: img: the image to draw
@ param: text: the text to draw
@ param: box: the box to draw
@ return: the image with box and text
"""
def cv2ImgAddText(img, text, box):
    x1, y1, x2, y2 = [int(box[j]) for j in range(4)] 
    fontsize = int ((x2 - x1) / text.__len__() * 1.5)
    textboxcolor = (50, 50, 255)
    boxcolor = textboxcolor
    fontcolor = (255, 255, 255)
    font = ImageFont.truetype("LPRNet/data/NotoSansCJK-Regular.ttc", fontsize, encoding="utf-8") # use in main.py
    # font = ImageFont.truetype("data/NotoSansCJK-Regular.ttc", fontsize, encoding="utf-8") # use in LPRNet_Test.py

    if y1 - fontsize > 0:
        # 识别文字在上方显示
        cv2.rectangle(img, (x1, y1), (x2, y2), boxcolor, 2, cv2.LINE_AA)
        cv2.rectangle(img, (x1, y1 - fontsize), (x2, y1), textboxcolor, -1)
        data = Image.fromarray(img)
        draw = ImageDraw.Draw(data)
        draw.text((x1 + ((x2 - x1) - text.__len__() * fontsize / 1.5), y1 - fontsize - fontsize / 4), text, fontcolor, font = font)
    else:
        # 识别文字在下方显示
        cv2.rectangle(img, (x1, y1), (x2, y2), boxcolor, 2, cv2.LINE_AA)
        cv2.rectangle(img, (x1, y2), (x2, y2 + fontsize), textboxcolor, -1)
        data = Image.fromarray(img)
        draw = ImageDraw.Draw(data)
        draw.text((x1 + ((x2 - x1) - text.__len__() * fontsize / 1.5), y2 - fontsize / 4), text, fontcolor, font = font)

    
    res = np.asarray(data)

    return res

def decode(preds, CHARS):
    # greedy decode
    pred_labels = list()
    labels = list()
    for i in range(preds.shape[0]):
        pred = preds[i, :, :]
        pred_label = list()
        for j in range(pred.shape[1]):
            pred_label.append(np.argmax(pred[:, j], axis=0))
        no_repeat_blank_label = list()
        pre_c = pred_label[0]
        for c in pred_label: # dropout repeate label and blank label
            if (pre_c == c) or (c == len(CHARS) - 1):
                if c == len(CHARS) - 1:
                    pre_c = c
                continue
            no_repeat_blank_label.append(c)
            pre_c = c
        pred_labels.append(no_repeat_blank_label)
        
    for i, label in enumerate(pred_labels):
        lb = ""
        for i in label:
            lb += CHARS[i]
        labels.append(lb)
    
    return labels, np.array(pred_labels)  

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='LPR Demo')
    # parser.add_argument("-image", help='image path', default='data/ccpd_weather/吉BTW976.jpg', type=str)
    parser.add_argument("-image_path", help='image path', default='data/test/', type=str)
    args = parser.parse_args()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    lprnet = LPRNet(class_num=len(CHARS), dropout_rate=0)
    lprnet.to(device)
    lprnet.load_state_dict(torch.load('weights/Final_LPRNet_model.pth', map_location=lambda storage, loc: storage))
    lprnet.eval()
    
    STN = STNet()
    STN.to(device)
    STN.load_state_dict(torch.load('weights/Final_STN_model.pth', map_location=lambda storage, loc: storage))
    STN.eval()
    
    print("Successful to build network!")
    
    image_names = os.listdir(args.image_path)

    count = 0
    runtime = 0
    # since = time.time()
    for image_name in image_names:
        image_full_path = os.path.join(args.image_path, image_name)
        # image = cv2.imread(image_full_path)
        image = cv2.imdecode(np.fromfile(image_full_path, dtype=np.uint8), 1)
        im = cv2.resize(image, (94, 24), interpolation=cv2.INTER_CUBIC)
        im = (np.transpose(np.float32(im), (2, 0, 1)) - 127.5)*0.0078125
        data = torch.from_numpy(im).float().unsqueeze(0).to(device)  # torch.Size([1, 3, 24, 94]) 
        since = time.time()
        transfer = STN(data)
        preds = lprnet(transfer)
        preds = preds.cpu().detach().numpy()  # (1, 68, 18)
        
        labels, pred_labels = decode(preds, CHARS)
        runtime += time.time() - since
        # print("model inference in {:2.3f} seconds".format(time.time() - since))

        print("Predict image {:s} result: {:s}".format(image_name.split('.')[0], labels[0]))
        if labels[0] == image_name.split('.')[0]:
            count += 1

        # img = cv2ImgAddText(image, labels[0], (0, 0))
        # img = cv2ImgAddText(image, labels[0], bbox)
        
        # # Save cropped image and transformed image
        # cv2.imshow("cropped", image)

        # transformed_img = convert_image(transfer)
        # cv2.imshow('transformed', transformed_img)
        # cv2.imwrite('data/transformed_image.png', transformed_img)
        
        # # cv2.imshow("test", img)
        # cv2.waitKey()
        # cv2.destroyAllWindows()
    print("Accuracy: {:.2f}%".format(count / len(image_names) * 100))
    print("model inference in {:2.3f} seconds".format(runtime / len(image_names)))
    # print("model inference in {:2.3f} seconds".format((time.time() - since) / len(image_names)))
    