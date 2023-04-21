import cv2

image = cv2.imread('CL01_ZIC0/test_13.png')
image = cv2.flip(image, 1)
cv2.imshow("image", image)
cv2.imwrite('CL01_ZIC0/test_13_flipped.png', image)
cv2.waitKey(0)