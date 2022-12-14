import logging 
from os import listdir 
from os.path import splitext 
from pathlib import Path 
import numpy as np 
import torch 
from PIL import Image 
from torch.utils.data import Dataset 

class BasicDataset(Dataset):
    def __init__(self,images_dir:str,masks_dir,scale:float=1.0,mask_suffix:str = ''):
        self.images_dir = Path(images_dir)
        self.masks_dir = Path(masks_dir)
        assert 0 < scale <= 1, 'Scale must be between 0 and 1'
        self.scale = scale 
        self.mask_suffix = mask_suffix 

        self.ids = [splitext(file)[0] for file in listdir(images_dir) if not file.startswith('.')]
        if not self.ids:
            raise RuntimeError(f'No input file found in {images_dir}, make sure you put your images')
        logging.info(f'Creating dataset with {len(self.ids)} examples')

    def __len__(self):
        return len(self.ids) 

    def preprocess(pil_img, scale, is_mask):
        w, h = pil_img.size 
        newW, newH = int(scale*w), int(scale*h) 
        assert newW > 0 and newH > 0, 'scale is too small, resized images would have no pixel'
        pil_img = pil_img.resize((newW,newH), resample=Image.NEAREST if is_mask else Image.BICUBIC)
        img_ndarray = np.asarray(pil_img)

        if not is_mask:
            if img_ndarray.ndim == 2:
                img_ndarray = img_ndarray[np.newaxis,...]
            else:
                img_ndarray = img_ndarray.transpose((2,0,1))
        return img_ndarray 

    def load(filename):
        ext = splitext(filename)[1]
        if ext == '.npy':
            return Image.fromarray(np.load(filename))
        elif ext in ['.pt', '.pth']:
            return Image.fromarray(torch.load(filename).numpy())
        else:
            return Image.open(filename)

    def __getitem__(self, idx):
        name = self.ids[idx]
        mask_file = list(self.masks_dir.glob(name + self.mask_suffix + '.*'))
        img_file = list(self.images_dir.glob(name + '.*'))

        assert len(img_file) == 1, f'Either no image or multiple images found for the ID {name}: {img_file}'
        assert len(mask_file) == 1, f'Either no mask or multiple masks found for the ID {name}: {mask_file}'
        mask = self.load(mask_file[0])
        img = self.load(img_file[0])

        assert img.size == mask.size, \
            f'Image and mask {name} should be the same size, but are {img.size} and {mask.size}'

        img = self.preprocess(img, self.scale, is_mask=False)
        mask = self.preprocess(mask, self.scale, is_mask=True)

        return {
            'image': torch.as_tensor(img.copy()).float().contiguous(),
            'mask': torch.as_tensor(mask.copy()).long().contiguous()
                }
            #contiguous==True : ????????? ?????? ??????, ?????? ?????? ???????????? ?????? 
            #contiguous == False : ?????? ????????? ???????????? ?????? ?????? ?????? ???????????? ?????? 

class CarvanaDataset(BasicDataset):
    def __init__(self, images_dir, masks_dir, scale=1):
        super().__init__(images_dir, masks_dir, scale, mask_suffix = '_mask')
        