#Musk R CNN
import torch
from torchvision.models.detection import maskrcnn_resnet50_fpn
from torchvision.transforms import functional as F
import cv2
import matplotlib.pyplot as plt
import os
import glob
import pickle
from tqdm import tqdm
import numpy as np
from trainer import convert_to_corners
# Load Pretrained Mask R-CNN model
model = maskrcnn_resnet50_fpn(pretrained=True)
model.eval()

device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
model.to(device)
def load_image(image_path):
    # Read image with OpenCV
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert to RGB
    # Convert to tensor and normalize
    img_tensor = F.to_tensor(img).unsqueeze(0).to(device)  # Add batch dimension
    return img, img_tensor
def get_predictions(img_tensor):
    # Get model predictions
    outputs = model(img_tensor)[0]

    # Filter predictions by score threshold
    pred_boxes = outputs['boxes'].detach().cpu().numpy()
    pred_scores = outputs['scores'].detach().cpu().numpy()
    pred_classes = outputs['labels'].detach().cpu().numpy()

    # Keep only predictions above the threshold and 3 as cars
    high_conf_indices = pred_classes == 3
    pred_boxes = pred_boxes[high_conf_indices]
    pred_classes = pred_classes[high_conf_indices]

    return pred_boxes, pred_classes, pred_scores
def visualize_predictions(img, boxes, masks, labels, class_names):
    # Apply masks and draw bounding boxes on the image
    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = box.astype(int)

        # Draw the bounding box
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)

        # Label the bounding box
        label = class_names[labels[i]]
        cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

        # Apply mask
        mask = masks[i, 0] > 0.5
        img[mask] = [0, 255, 0]  # Green mask

    plt.imshow(img)
    plt.axis("off")
    plt.show()
# Define class names for COCO dataset
COCO_CLASSES = [
    "__background__", "person", "bicycle", "car", "motorcycle", "airplane",
    "bus", "train", "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag",
    "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
    "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana",
    "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza",
    "donut", "cake", "chair", "couch", "potted plant", "bed", "dining table",
    "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock",
    "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]

# Function to process a folder of images and return bounding boxes
def process_image_folder(image_path, ground_truth):

    original_img, img_tensor = load_image(image_path)
    # Get bounding boxes for the current image
    boxes, labels, scores = get_predictions(img_tensor)

    # Find matching ground truth and include that in the output

    output = {
        "predicted_boxes_corners": boxes,
        "predicted_scores": scores,
        "gt_boxes_corners": ground_truth
    }
    # Optionally visualize the bounding boxes
    # visualize_predictions(original_img, boxes, masks, labels, COCO_CLASSES)
    return output

def load_ground_truth(gt_dir, sub_folder, file_name):
    gt_fullname = os.path.join(gt_dir, sub_folder, file_name)

    if os.path.isfile(gt_fullname):
        with open(gt_fullname, "rb") as f:
            gt_data = pickle.load(f)

        gt_boxes_corners = []
        for cls, box in zip(gt_data["box_type"], gt_data["box_loc"]):
            if cls == 1:
                # convert tuple into a list
                box_loc = torch.tensor(box).unsqueeze(0)
                box_corner = convert_to_corners(box_loc)
                gt_boxes_corners.append(box_corner)

        return gt_boxes_corners
    else:
        # print(f"There are no matching file for {gt_fullname}. Investigate.")
        return None

# path to your folder
folder_path = "/home/meowater/Documents/ssd_drive/compressed_camera_images2/"
box_path = '/home/meowater/Documents/ssd_drive/maskRCNN_boxes/'
gt_path = '/home/meowater/Documents/ssd_drive/cam_box_per_image/'
img_list = glob.glob(os.path.join(folder_path, '*/*.jpg'), recursive=True)


for fn in tqdm(img_list):
    file_path, base_name = os.path.split(fn)
    context_name = file_path.split('/')[-1]

    name_prefix = context_name + '_' + base_name.split('.')[0]
    gt_name = name_prefix + '.pkl'
    gt_name = gt_name.replace('_camera-1_', '_camera_1_')
    # load groundtruth
    gt_boxes = load_ground_truth(gt_path, context_name, gt_name)

    if gt_boxes is not None:
        sub_save_path = os.path.join(box_path, context_name)
        os.makedirs(sub_save_path, exist_ok=True)
        new_fn = os.path.join(sub_save_path, name_prefix + '_maskCNN.pkl')
        box_output = process_image_folder(fn, gt_boxes)

        with open(new_fn, 'wb') as handle:
            pickle.dump(box_output, handle, protocol=pickle.HIGHEST_PROTOCOL)