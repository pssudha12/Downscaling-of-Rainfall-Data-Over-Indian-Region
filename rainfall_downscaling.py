# -*- coding: utf-8 -*-
"""Rainfall downscaling

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1a_GKrGll4gERh39zyzaXfzIrnAKrmsKi
"""

!pip install basemap

import tensorflow as tf
import glob
import numpy as np
from sklearn import preprocessing
import keras
from keras.layers import Dense, Dropout,Conv2D, Flatten, Activation, BatchNormalization
from keras.models import Sequential
from keras.optimizers import Adam ,SGD
from keras.layers import PReLU, LeakyReLU
from keras.initializers import RandomNormal,TruncatedNormal,glorot_normal
np.seterr(divide='ignore', invalid='ignore')

import xarray as xr
import matplotlib.pyplot as plt
import h5py
import keras
from keras import regularizers
from keras.models import load_model
import math as m
from mpl_toolkits import basemap
from netCDF4 import Dataset

# 1-0.5 summer monsoon rainfall data
xf=xr.open_dataset("/content/0.25-1-0.5_2005-2009.nc")
rf=xf["rf"].values
rf1=np.array(rf)
a=rf.shape
print(rf.shape)
z=a[0]


latl=xf["lat"].values
lonl=xf["lon"].values

xf.close()
#Dimensions:  (time: 605, lat: 65, lon: 69)

# 0.25-0.5 data
xf=xr.open_dataset("/content/0.25-0.5_2005-2009.nc")
rf=xf["rf"].values
rf2=np.array(rf)
rf2_=np.array(rf)
print(rf.shape)


lat2=xf["lat"].values
lon2=xf["lon"].values

xf.close()

# actual 0.25 resolution summer monsoon rainfall data 
# 0.25 data (groundtruth | size: 129 x 135)
xf=xr.open_dataset("/content/0.25_JJAS_2005-2009.nc")
rf=xf["rf"].values
rf4=np.array(rf)
rf4_=np.array(rf)
print(rf.shape)


lat4=xf["lat"].values
lon4=xf["lon"].values

xf.close()

xf=xr.open_dataset("/content/0.25-1-0.5_1995_2004.nc")
rfL1=xf['rf'].values
rfL1=np.array(rfL1)
a=np.shape(rfL1)
print(a)         
xf.close()

xf=xr.open_dataset("/content/0.25-0.5_1995_2004.nc")
rfH1=xf['rf'].values          
rfH1=np.array(rfH1)
print(rfH1.shape)          
xf.close()

xf=xr.open_dataset("/content/0.25-0.5-0.25_1995_2004.nc")
rfL2=xf['rf'].values          
rfL2=np.array(rfL2)
print(rfL2.shape)          
xf.close()

xf=xr.open_dataset("/content/0.25_1995-2004.nc")
rfH2=xf['rf'].values          
rfH2=np.array(rfH2) 
print(rfH2.shape)         
xf.close()

# function for mapping from 1 shape to desired shape (like 150 x 150) 
# for the 0.25-0.5 data summer monsoon rainfall data
def transform2(a):
    l=np.empty((a.shape[0],150,150))
    l[:]=np.nan
    for i in range(a.shape[0]):
      for j in range(a.shape[1]):
        for k in range(a.shape[2]):
          l[i,j+6+5,k+2+5]=a[i,j,k] 
    return l

# function for mapping from 1 shape to desired shape (like 82 x 82) 
# for the 1-0.5 data summer monsoon rainfall data
def transform1(a):
    l=np.empty((a.shape[0],82,82))
    l[:]=np.nan
    for i in range(a.shape[0]):
      for j in range(a.shape[1]):
        for k in range(a.shape[2]):
          l[i,j+9,k+6]=a[i,j,k] 
    return l

# function for mapping from 1 shape to desired shape (like 150 x 150) 
# for the 0.25 data summer monsoon rainfall data
def transform(a): #for 129,135
    l=np.empty((a.shape[0],150,150))
    l[:]=np.nan
    for i in range(a.shape[0]):
      for j in range(a.shape[1]):
        for k in range(a.shape[2]):
          l[i,j+6+5,k+1+5]=a[i,j,k] 
    return l
    
def negtonan1(a):
  for i in range(a.shape[0]):  
    for j in range(a.shape[1]):
      for k in range(a.shape[2]):
        if(a[i,j,k]<=0):
          print(a[i,j,k])
          a[i,j,k]=0  
  return a

# function for negative to NaN
def negtonan(a):
  for i in range(a.shape[0]):  
    for j in range(a.shape[1]):
      for k in range(a.shape[2]):
        if(a[i,j,k]<0.00):
          a[i,j,k]=np.nan  
  return a
  
# function to convert NaN to 0
def nanto0(a):
 for i in range(a.shape[0]):       
    for j in range(a.shape[1]):
      for k in range(a.shape[2]):
        if(np.isnan(a[i,j,k])):
          a[i,j,k]=0
 return a

#making full image (array) from patches (sub array)
def merge(images, size):
  h, w = images.shape[1], images.shape[2]
  img = np.zeros((h*size[0], w*size[1], 1))
  for idx, image in enumerate(images):
    i = idx % size[1]
    j = idx // size[1]
    img[j*h:j*h+h, i*w:i*w+w, :] = image

  return img

## Constructor  
# It is the constructor of the class srcnn. Whenever taken 
# any instant of this class, immediately all these values will be initialised.
class srcnn():
  def __init__(self,image_size,stride,batch_size,epochs,input_,label,lr):
    self.image_size=image_size
    self.label_size=self.image_size-12
    self.stride=stride
    self.batch_size=batch_size
    self.epochs=epochs
    self.input_=input_
    self.label=label
    self.lr=lr
    
    self.build_model()
  
  ## Defining model architecture (based on Dong et al. paper)  
  # In Dong et al., there are 3 layers
  def build_model(self):
    self.model=Sequential()            ##building a sequential model
    
    ## 1st ConV  layer -->   input layer [kernel (9x9)], choosing 9 x 9 depends on the experiments
    # It is the 1 Conv2D layer. Conv2D function is coming from the lib keras.layers
    self.model.add(Conv2D(64,(9,9), padding='valid',data_format=None,dilation_rate=(1, 1),
    use_bias=True, kernel_initializer=RandomNormal(mean=0.0, stddev=1e-3, seed=None), 
    # did initialisation in input shape
    bias_initializer='zeros', kernel_regularizer=None, bias_regularizer=None,
    activity_regularizer=None, kernel_constraint=None, bias_constraint=None,
    input_shape=(self.image_size,self.image_size,1))) # These is 1 channel here                                          #-- last argument is for #channels (1 in this case).
    
    self.model.add(PReLU(alpha_initializer='zeros', weights=None))

    self.model.add(BatchNormalization())                                                       ## Normalization [0,1] for 1st layer
    # here patching is done means, if 1 layer is given, we do the patching.
    # Passed this patch to second layer which does the non-linearisation and transform this patch to hr

    ## 2nd ConV  layer    Flattening layer [kernel (1x1)]
    # It is the second layer.
    self.model.add(Conv2D(32,(1,1), padding='valid',data_format=None,
    use_bias=True, kernel_initializer=TruncatedNormal(mean=0.0, stddev=1e-3, seed=None),  #----------------------
    bias_initializer='zeros', kernel_regularizer=None, bias_regularizer=None,
    activity_regularizer=None, kernel_constraint=None, bias_constraint=None))
    
    self.model.add(PReLU(alpha_initializer='zeros', weights=None))
  
    
    self.model.add(BatchNormalization())                                                  ## Normalization [0,1] for 2nd layer
    # Finally when this patch is ready, with the high resolution patch, whole image will be reconstructed
    ## ConV 3 layer     image reconstruction layer [kernel (5x5)] | Output layer
    self.model.add(Conv2D(1,kernel_size=(5,5), padding='valid',data_format=None,
    use_bias=True, kernel_initializer=glorot_normal(seed=None),                           #-----------------------
    bias_initializer='zeros', kernel_regularizer=None, bias_regularizer=None,
    activity_regularizer=None, kernel_constraint=None, bias_constraint=None))
    
    self.model.add(PReLU(alpha_initializer='zeros', weights=None))
    
    ## No normalization  bacause of output layer
    # Before writing the model, set what is the loss and optimiser function.

    ## Optimizaer = Adam  | Loss function = MSE and accuracy is based on learning rate.
    # using this, we are optimising our approximation for z = Wx+b, where w is weight, x is the input and b is the bias vector
    # and we're doing the computationn between w and x.
    self.opti= Adam(lr=self.lr)  
    self.model.compile(optimizer=self.opti, loss='mean_squared_error', metrics=['accuracy'])
    # finally taken the model summary.
    self.model.summary()
  # this is the whole model function


  ## function to generate patches 
  # prepare_data is data taken to use before putting it in the model. 
  # this prepare function is used to divide the image.
  # It is preparing the data to give to the input. We are dividing the whole data and one by one 
  # patch is going and we make the hr.
  def prepare_data(self):
    padding=6
    sub_input_sequence = []
    sub_label_sequence = []
    _,h,w=self.input_.shape     # Getting shape of input
                                ## _ = #samples h=height, w= width
    
    # no_sample
    for i in range(_):
      input_=self.input_[i]
      label=self.label[i]
      
      ## making patches of (35x35) from data size of (140x140), and dividing the whole image.
      for x in range(0,h-self.image_size+1,self.stride):
        for y in range(0,w-self.image_size+1,self.stride):
        
          sub_input=input_[x:x+self.image_size,y:y+self.image_size]                                    ##input patch
          sub_label=label[x+padding:x+padding+self.label_size,y+padding:y+padding+self.label_size]     ##ground-truth patch
          
          sub_input = sub_input.reshape([self.image_size,self.image_size, 1])  
          sub_label = sub_label.reshape([self.label_size,self.label_size, 1])
          
          ## Appending patches in corresponding arrays
          sub_input_sequence.append(sub_input)
          sub_label_sequence.append(sub_label)
    # end of for loops (i,x,y)
    
    # converting the list to the array
    self.arrdata = np.array(sub_input_sequence) # [?, 33, 33, 1]
    self.arrlabel = np.array(sub_label_sequence) # [?, 21, 21, 1] 
    # Then this go to the training set.
  def training1(self):
  
  ## 5 parameters are required [x,y,epoch,batchsize, validation split] 
  # training function is training the model.
   # Function fit: Used for training 
   #level 1 = 1 degree to 0.5 degree downscaling
   
    history=self.model.fit(self.arrdata,self.arrlabel,epochs=self.epochs,batch_size=self.batch_size,validation_split=0.3)
    eloss=history.history['loss']
    evloss=history.history['val_loss']
    eacc=history.history['acc']
    evacc=history.history['val_acc']
    
    #np.savez("/content/1_stacked_final.npz",eloss=eloss,evloss=evloss,eacc=eacc,evacc=evacc)  
    
    self.model.save("/content/1_stacked_final.h5")
       
  def training2(self):
  
  ## 5 parameters are required [x,y,epoch,batchsize, validation split] 
   # Function fit: Used for training 
   #level 2 = 0.5 degree to 0.25 degree downscaling
   
    history=self.model.fit(self.arrdata,self.arrlabel,epochs=self.epochs,batch_size=self.batch_size,validation_split=0.3) 
    eloss=history.history['loss']
    evloss=history.history['val_loss']
    eacc=history.history['acc']
    evacc=history.history['val_acc']
    
    #np.savez("/content/2_stacked_final.npz",eloss=eloss,evloss=evloss,eacc=eacc,evacc=evacc) 
    
    self.model.save("/content/2_stacked_final.h5")

#-----------------------------------------------------------------------------------------------------------------------------------------------
## To make a square matrix, data mtrix was
##  generated of size 140x140 by padding NaN value
##..... Developed routine for padding...
 
input_1=wmpreprocess(rfL1,n,0,70,3,0)
label_1=wmpreprocess(rfH1,n,0,70,3,0)
  
input_2=wmpreprocess(rfL2,n,0,140,6,1)
label_2=wmpreprocess(rfH2,n,0,140,6,2)

print(input_1.shape)
print(label_1.shape)
print(input_2.shape)
print(label_2.shape)

#call SRCNN class for level 1.
# Here the srcnn function is called. It has so many epochs.
# In each epoch, those 3 layers will be called.
# then checked this learning rate. For reaching this 10^-4, we need to go atleast 500-1000 iterations.

s1=srcnn(image_size=22,stride=8,batch_size=200,epochs=10,input_=input_1,label=label_1,lr=10**-4)
s1.prepare_data()
s1.training1()

#call SRCNN class for level 2
s2=srcnn(image_size=35,stride=15,batch_size=200,epochs=10,input_=input_2,label=label_2,lr=10**-4)
s2.prepare_data()
s2.training2()
# Once all the epochs are finished, then it will start saving the model and saving that h5 file.

# In testing, got whole data and printing image of a particular day of the rainfall.

def test(d,rf1,rf2,rf4):

  interp=rf1[d,:,:]
  interp=np.reshape(interp,(1,interp.shape[0],interp.shape[1]))

  interp=transform1(interp)             # transform  both lr & hr to 82,82
  rf2=transform1(rf2)
  interp=np.reshape(interp,(interp.shape[1],interp.shape[2]))   
  interp=np.reshape(interp,(1,interp.shape[0],interp.shape[1]))

  interp= negtonan(interp)             # convert negative to nan
  interp=np.reshape(interp,(interp.shape[1],interp.shape[2]))      
  interp=np.reshape(interp,(1,interp.shape[0],interp.shape[1]))

  interp= nanto0(interp)               # convert all nan values to 0
  interp=np.reshape(interp,(interp.shape[1],interp.shape[2]))
   # slicing the image to 22,22
  
  h,w=interp.shape
  padding=6
  img_size=22             # img_size should be same in training and testing
  label_size=10 
  stride =10              # stride= img_size - 12 (for testing)
  sub_input_sequence = []
  sub_label_sequence = []
  nx=ny=0
  for i in range(1):
    input_=interp
  
    for x in range(0,h-img_size+1,stride):
      nx+=1
      ny=0
      for y in range(0,w-img_size+1,stride):
        ny+=1
        sub_input=input_[x:x+img_size,y:y+img_size]
     
        
        sub_input = sub_input.reshape([img_size,img_size, 1])  
     
    
        sub_input_sequence.append(sub_input)
       
        
    arrdata = np.array(sub_input_sequence) # [?, 35, 35, 1]  
  
  # 'arrdata' is thefinal sliced array going into the trained model

  model= load_model("/content/1_stacked_final.h5",compile=False) # paste the path of trained model to be     loaded

  ans=model.predict(arrdata)
 
  ans=np.reshape(ans,(ans.shape[0],ans.shape[1],ans.shape[2],1))  # 'ans' is the output
  img=merge(ans,[nx,ny])                                          # merging the output 'ans'          
  img=np.reshape(img ,(img.shape[0],img.shape[1]))  
   

  l=np.empty((1,82,82))
  l[:]=np.nan

  for i in range(70):
          for j in range(70):
              l[0,i+6,j+6]=img[i,j]
  
  l=l[0,9:74,7:75]           

  h=[]

  lonn,latn=np.meshgrid(lon4,lat4)

  znew = basemap.interp(l, lon2, lat2, lonn, latn, order=1)
  h.append(znew)
  rf3=np.array(h) 

#-----------------------------------------------------------------------------------------------------------------------------------------------

  interp=rf3
  interp=transform2(interp)             # transform  both lr & hr to 150,150
  rf4=transform2(rf4)
  interp=np.reshape(interp,(interp.shape[1],interp.shape[2]))   
  interp=np.reshape(interp,(1,interp.shape[0],interp.shape[1]))

  interp= negtonan(interp)             # convert negative to nan
  interp=np.reshape(interp,(interp.shape[1],interp.shape[2]))      
  interp=np.reshape(interp,(1,interp.shape[0],interp.shape[1]))


  interp= nanto0(interp)               # convert all nan values to 0
  interp=np.reshape(interp,(interp.shape[1],interp.shape[2]))
    
  # slicing the image to 35,35
  
  h,w=interp.shape
  padding=6
  img_size=35             # img_size should be same in training and testing
  label_size=23 
  stride =23              # stride= img_size - 12 (for testing)
  sub_input_sequence = []
  sub_label_sequence = []
  nx=ny=0
  for i in range(1):
    input_=interp
      
    for x in range(0,h-img_size+1,stride):
      nx+=1
      ny=0
      for y in range(0,w-img_size+1,stride):
        ny+=1
        sub_input=input_[x:x+img_size,y:y+img_size]
     
      
        sub_input = sub_input.reshape([img_size,img_size, 1])  
   
  
        sub_input_sequence.append(sub_input)
     
      
    arrdata = np.array(sub_input_sequence) # [?, 35, 35, 1]  
  
  # 'arrdata' is thefinal sliced array going into the trained model
## here we are removing the model. Loading the model which is stored and saved in .h5
# Once we are reading the model, we are calling this model and putting our input data

  model= load_model("/content/2_stacked_final.h5",compile=False) # paste the path of trained model to be loaded

  ans=model.predict(arrdata)
  
  ans=np.reshape(ans,(ans.shape[0],ans.shape[1],ans.shape[2],1))  # 'ans' is the output
  img=merge(ans,[nx,ny])                                          # merging the output 'ans'          
  img=np.reshape(img ,(img.shape[0],img.shape[1]))
    
  l=np.empty((1,150,150))
  l[:]=np.nan

  for i in range(138):
          for j in range(138):
              l[0,i+6,j+6]=img[i,j]

  for i in range(150):
    for j in range(150):
      if(np.isnan(rf4[d,i,j])):
        l[0,i,j]=np.nan
  
  l=l[0,11:140,7:142]
  
  return l
  
rfl=[]
  
for d in range(z):
   
    x=test(d,rf1,rf2,rf4)
    rfl.append(x)



a=lon4
b=lat4

def net(name,value):
  dataset=Dataset(name,"w")
  no_dim=dataset.createDimension('no',z) #10950=365*30  365*no of years
  
  lat_dim = dataset.createDimension('lat',b.shape[0])
  lon_dim = dataset.createDimension('lon',a.shape[0])
  
  var_dim=dataset.createDimension('rf',None)
  var=dataset.createVariable('rf',np.float32,('no','lat','lon',))
  
  no = dataset.createVariable('no', np.float32,('no',))

  latitudes = dataset.createVariable('lat', np.float32,('lat',))
  longitudes = dataset.createVariable('lon', np.float32,('lon',))
  
  latitudes.units = 'degree_north'
  longitudes.units = 'degree_east' 
  
  latitudes[:] = b
  longitudes[:] = a
  no[:]=np.arange(0,z)

  var.units='mm'
  var[:]=value
   
  dataset.close()  

rfl=np.array(rfl)  
print(rfl.shape)
net('/content/stack_rtgop.nc',rfl) # d5inter for low resolution , d5grnd for high resolution

d=int(input ("Enter the number of day to test (d= 1-365) : "))

# Give the directory of file which we want to test / 0.5 from 1 degree
xf=xr.open_dataset('/content/1-0.5_2006.nc')
rf=xf["rf"].values
rf1=np.array(rf)
print(rf.shape)

latl=xf["lat"].values
lonl=xf["lon"].values

plt.contourf(lonl,latl,rf1[d,:,:],cmap='rainbow')  #lowres input after interpolate
plt.colorbar()
plt.savefig('/content/1deginput_stacked_srcnn.png', dp=300)
plt.close()

xf.close()

# Give the directory of file which we want to test / 0.5 from 0.25 degree
xf=xr.open_dataset('/content/0.25-0.5_2006.nc')
rf=xf["rf"].values
rf2=np.array(rf)
rf2_=np.array(rf)
print(rf.shape)

lat2=xf["lat"].values
lon2=xf["lon"].values

plt.contourf(lon2,lat2,rf2[d,:,:],cmap='rainbow')  #lowres input after interpolate
plt.colorbar()
plt.savefig('/content/0.5groundtruth_stacked_srcnn.png', dp=300)
plt.close()

xf.close()

# Give the directory of file which we want to test / 0.25 degree data (HR) of same year
xf=xr.open_dataset('/content/0.25_2006.grd')
rf=xf["rf"].values
rf4=np.array(rf)
rf4_=np.array(rf)
print(rf.shape)

lat4=xf["lat"].values
lon4=xf["lon"].values

plt.contourf(lon4,lat4,rf4[d,:,:],cmap='rainbow')  #lowres input after interpolate
plt.colorbar()
plt.savefig('/content/0.25groundtruth_stacked_srcnn.png', dp=300)
plt.close()

xf.close()

def transform2(a):
    l=np.empty((a.shape[0],150,150))
    l[:]=np.nan
    for i in range(a.shape[0]):
      for j in range(a.shape[1]):
        for k in range(a.shape[2]):
          l[i,j+6+5,k+2+5]=a[i,j,k] 
    return l
    
def transform1(a):
    l=np.empty((a.shape[0],82,82))
    l[:]=np.nan
    for i in range(a.shape[0]):
      for j in range(a.shape[1]):
        for k in range(a.shape[2]):
          l[i,j+9,k+6]=a[i,j,k] 
    return l
  
def negtonan(a):
  for i in range(a.shape[0]):  
    for j in range(a.shape[1]):
      for k in range(a.shape[2]):
        if(a[i,j,k]<0.00):
          a[i,j,k]=np.nan  
  return a
   
def nanto0(a):

  for i in range(a.shape[0]):  
    for j in range(a.shape[1]):
      for k in range(a.shape[2]):
        if(np.isnan(a[i,j,k])):
          a[i,j,k]=0
        
  return a        
   
def merge(images, size):
  h, w = images.shape[1], images.shape[2]
  img = np.zeros((h*size[0], w*size[1], 1))
  for idx, image in enumerate(images):
    i = idx % size[1]
    j = idx // size[1]
    img[j*h:j*h+h, i*w:i*w+w, :] = image

  return img

interp=rf1[d,:,:]
print(interp.shape)
interp=np.reshape(interp,(1,interp.shape[0],interp.shape[1]))
print(interp.shape)

interp=transform1(interp)             # transform  both lr & hr to 82,82
rf2=transform1(rf2)
interp=np.reshape(interp,(interp.shape[1],interp.shape[2]))   
interp=np.reshape(interp,(1,interp.shape[0],interp.shape[1]))

interp= negtonan(interp)             # convert negative to nan
interp=np.reshape(interp,(interp.shape[1],interp.shape[2]))      
interp=np.reshape(interp,(1,interp.shape[0],interp.shape[1]))

            

interp= nanto0(interp)               # convert all nan values to 0
interp=np.reshape(interp,(interp.shape[1],interp.shape[2]))
    
# slicing the image to 22,22
  
h,w=interp.shape
padding=6
img_size=22             # img_size should be same in training and testing
label_size=10 
stride =10              # stride= img_size - 12 (for testing)
sub_input_sequence = []
sub_label_sequence = []
nx=ny=0
for i in range(1):
  input_=interp
  
  for x in range(0,h-img_size+1,stride):
    nx+=1
    ny=0
    for y in range(0,w-img_size+1,stride):
      ny+=1
      sub_input=input_[x:x+img_size,y:y+img_size]
   
      
      sub_input = sub_input.reshape([img_size,img_size, 1])  
   
  
      sub_input_sequence.append(sub_input)
     
      
  arrdata = np.array(sub_input_sequence) # [?, 35, 35, 1]
  #arrlabel = np.array(sub_label_sequence) # [?, 23, 23, 1]   
  
print(nx,ny) 
print(arrdata.shape)                                     # 'arrdata' is thefinal sliced array going into the trained model

model= load_model("/content/1_stacked_final.h5",compile=False) # paste the path of trained model to be loaded

ans=model.predict(arrdata)
print(ans.shape)
ans=np.reshape(ans,(ans.shape[0],ans.shape[1],ans.shape[2],1))  # 'ans' is the output
img=merge(ans,[nx,ny])                                          # merging the output 'ans'          
img=np.reshape(img ,(img.shape[0],img.shape[1]))
print(img.shape)

lonn=np.linspace(lon2[0],lon2[-1],70)
latn=np.linspace(lat2[0],lat2[-1],70)  

l=np.empty((1,82,82))
l[:]=np.nan

for i in range(70):
        for j in range(70):
            l[0,i+6,j+6]=img[i,j]
    

l=l[0,9:74,6:75]
print(l.shape)

h=[]

lonn,latn=np.meshgrid(lon4,lat4)

znew = basemap.interp(l, lon2, lat2, lonn, latn, order=1)
h.append(znew)

rf3=np.array(h)   
print(rf3.shape)

#-----------------------------------------------------------------------------------------------------------------------------------------------

interp=rf3
interp=transform2(interp)             # transform  both lr & hr to 150,150
rf4=transform2(rf4)
interp=np.reshape(interp,(interp.shape[1],interp.shape[2]))   
interp=np.reshape(interp,(1,interp.shape[0],interp.shape[1]))

interp= negtonan(interp)             # convert negative to nan
interp=np.reshape(interp,(interp.shape[1],interp.shape[2]))      
interp=np.reshape(interp,(1,interp.shape[0],interp.shape[1]))


interp= nanto0(interp)               # convert all nan values to 0
interp=np.reshape(interp,(interp.shape[1],interp.shape[2]))
    
# slicing the image to 35,35
  
h,w=interp.shape
padding=6
img_size=35             # img_size should be same in training and testing
label_size=23 
stride =23              # stride= img_size - 12 (for testing)
sub_input_sequence = []
sub_label_sequence = []
nx=ny=0
for i in range(1):
  input_=interp
  
  for x in range(0,h-img_size+1,stride):
    nx+=1
    ny=0
    for y in range(0,w-img_size+1,stride):
      ny+=1
      sub_input=input_[x:x+img_size,y:y+img_size]
   
      
      sub_input = sub_input.reshape([img_size,img_size, 1])  
   
  
      sub_input_sequence.append(sub_input)
     
      
  arrdata = np.array(sub_input_sequence) # [?, 35, 35, 1]
  #arrlabel = np.array(sub_label_sequence) # [?, 23, 23, 1]   
  
print(nx,ny) 
print(arrdata.shape)                                     # 'arrdata' is thefinal sliced array going into the trained model

model= load_model("/content/2_stacked_final.h5",compile=False) # paste the path of trained model to be loaded

ans=model.predict(arrdata)
print(ans.shape)
ans=np.reshape(ans,(ans.shape[0],ans.shape[1],ans.shape[2],1))  # 'ans' is the output
img=merge(ans,[nx,ny])                                          # merging the output 'ans'          
img=np.reshape(img ,(img.shape[0],img.shape[1]))
print(img.shape)

lonn=np.linspace(lon4[0],lon4[-1],138)
latn=np.linspace(lat4[0],lat4[-1],138)  

l=np.empty((1,150,150))
l[:]=np.nan

for i in range(138):
        for j in range(138):
            l[0,i+6,j+6]=img[i,j]

for i in range(150):
  for j in range(150):
    if(np.isnan(rf4[d,i,j])):
      l[0,i,j]=np.nan

lonn=np.linspace(lon4[0],lon4[-1],135)
latn=np.linspace(lat4[0],lat4[-1],129)
print(np.nanmin(l),np.nanmax(l),'Predicted')

c=plt.contourf(lonn,latn,l[0,11:140,7:142],cmap='rainbow')#,levels=[0,8,16,24,32,40,48,56,64]
plt.colorbar()
plt.savefig('/content/predicted_stacked_srcnn.png', dp=300)
plt.close()  

     
plt.contourf(lon4,lat4,rf4_[d,:,:],cmap='rainbow',extend='max',levels=c.levels)
print(np.nanmin(rf4_[d,:,:]),np.nanmax(rf4_[d,:,:]),'Ground truth')
plt.colorbar()
plt.savefig('/content/ground_truth_with_prediction_scale.png', dp=300)
plt.close()

import numpy as np
import xarray as xr
from netCDF4 import Dataset
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error
import seaborn as sns
import statistics

def correlate(rf,rf1):
   crf=[]
   a=rf.shape[0]
   print(rf1.shape)
   print(rf.shape)  
   for z in range(a):
   
      h=np.corrcoef(rf[z,:], rf1[z,:],rowvar=True)
      v=h[1,0]
      crf.append(v)
      
   return crf

def mse(rf,rf1):
   mse=[]
   a=rf.shape[0]
   print(rf1.shape)
   print(rf.shape)  
   for z in range(a):
   
      h=mean_squared_error(rf[z,:],rf1[z,:])
      mse.append(h)
      
   return mse

xf=xr.open_dataset("/content/0.25_JJAS_2005-2009.nc")
rf=xf["rf"].values
lato=xf["lat"].values
lono=xf["lon"].values
a=rf.shape[0]
rf=np.array(rf)
print(rf.shape)


rf=rf[np.logical_not(np.isnan(rf))]
print(rf.shape)
RF=np.reshape(rf,(a,rf.shape[0]//a))
print(RF.shape)
FRF=RF.flatten()

xf.close()

xf=xr.open_dataset("/content/1-0.25_imd_JJAS_2005-2009.nc")
rf=xf["rf"].values
rf=np.array(rf)
print(rf.shape)
a=rf.shape[0]
#rf=rf-c


rf=rf[np.logical_not(np.isnan(rf))]
print(rf.shape)
RFN=np.reshape(rf,(a,rf.shape[0]//a))
print(RFN.shape)
FRFN=RFN.flatten()

xf.close()

xf=xr.open_dataset("/content/stack_rtgop.nc")
rf=xf["rf"].values
lato=xf["lat"].values
lono=xf["lon"].values
rf=np.array(rf)
a=rf.shape[0]
#rf=rf-c

rf=rf[np.logical_not(np.isnan(rf))]
print(rf.shape)
RFSR=np.reshape(rf,(a,rf.shape[0]//a))
print(RFSR.shape)
FRFSR=RFSR.flatten()

xf.close()

C=correlate(RF,RFSR)
X=correlate(RF,RFN)

N=mse(RF,RFSR)
B=mse(RF,RFN)

bin=np.arange(0,1.01,0.01)

sns.distplot(C, hist=False, kde=True, 
             bins = bin, color = 'red',label = 'STACK', 
             kde_kws={'linewidth': 4})

sns.distplot(X, hist=False, kde=True, 
             bins = bin, color = 'blue',label = 'LINEAR-INTERPOLATE',
             kde_kws={'linewidth': 4})

   
plt.legend()
plt.xlabel('CORRELATION', fontsize=21)
plt.ylabel('PDF',fontsize=21)
ax=plt.gca()
ax.set_facecolor((0.73,0.73,0.73))
ax.tick_params(labelsize='x-large')
plt.tight_layout()
plt.savefig('/content/Correlation.png',dpi=400,format='png',figsize=(5,9))

plt.xlim(-0.3,1.02)

bin=np.arange(0,1000,20)             
             
sns.distplot(N, hist=False, kde=True, 
             bins = bin, color = 'green',label = 'STACK', 
             kde_kws={'linewidth': 4})

sns.distplot(B, hist=False, kde=True, 
             bins = bin, color = 'blue',label = 'LINEAR-INTERPOLATE',
             kde_kws={'linewidth': 4})
             
           
plt.legend()
plt.xlabel('MSE',fontsize=21)
plt.ylabel('PDF',fontsize=21)
plt.xlim(-50,550)
plt.ylim(0.00015,0.0050)

ax=plt.gca()
ax.set_facecolor((0.73,0.73,0.73))
ax.tick_params(labelsize='x-large')
plt.tight_layout()
plt.savefig('/content/MSE.png',dpi=400,format='png')

