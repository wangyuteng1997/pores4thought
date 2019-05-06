# -*- coding: utf-8 -*-
"""
Created on Mon Feb 25 14:55:38 2019

@author: ag4915
"""
    
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.utils as vutils
from torchvision.utils import save_image
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import random
import argparse
import os
from hdf5_io import save_hdf5
from torch.autograd import Variable
import torchvision.transforms as transforms
from dataset_test import HDF5Dataset

from dcgan_3d import Generator, Discriminator

# Set random seed for reproducibility.
seed = 500
random.seed(seed)
torch.manual_seed(seed)
print("Random Seed: ", seed)


parser = argparse.ArgumentParser()
parser.add_argument('--dataroot', default='', help='input dataset file')
parser.add_argument('--cuda', action='store_true', help='enables cuda')
parser.add_argument('--ngpu', type=int, default=1, help='number of GPUs to use')
parser.add_argument('--bsize', default=64, help='batch size during training')
parser.add_argument('--imsize', default=64, help='size of training images')
parser.add_argument('--nc', default=3, help='number of channels')
parser.add_argument('--nz', default=100, help='size of z latent vector')
parser.add_argument('--ngf', default=128, help='size of feature maps in generator')
parser.add_argument('--ndf', default=64, help='size of feature maps in discriminator')
parser.add_argument('--nepochs', default=15, help='number of training epochs')
parser.add_argument('--lr', default=0.0002, help='learning rate for optimisers')
parser.add_argument('--beta1', default=0.5, help='beta1 hyperparameter for Adam optimiser')
parser.add_argument('--save_epoch', default=2, help='step for saving paths')
parser.add_argument('--sample_interval', default=50, help='output image step')

opt = parser.parse_args()

opt.dataroot = 'test_threephase_3D'
ngpu = int(opt.ngpu)
nz = int(opt.nz)
ngf = int(opt.ngf)
ndf = int(opt.ndf)
nc = int(opt.nc)

# Use GPU is available else use CPU.
device = torch.device("cuda:0" if(torch.cuda.is_available()) else "cpu")
print(device, " will be used.\n")

# Get the data.
dataset = HDF5Dataset(opt.dataroot,
                          input_transform=transforms.Compose([
                          transforms.ToTensor()
                          ]))

dataloader = torch.utils.data.DataLoader(dataset,
        batch_size=opt.bsize,
        shuffle=True)

sample_batch = next(iter(dataloader))
#print(sample_batch.shape)

#os.makedirs('images', exist_ok=True)
os.makedirs('images_3D', exist_ok=True)
os.makedirs('threephase_model', exist_ok=True)

def weights_init(w):
    """
    Initializes the weights of the layer, w.
    """
    classname = w.__class__.__name__
    if classname.find('Conv') != -1:
        nn.init.normal_(w.weight.data, 0.0, 0.02)
    elif classname.find('BatchNorm') != -1:
        nn.init.normal_(w.weight.data, 1.0, 0.02)
        nn.init.constant_(w.bias.data, 0)

# Create the generator.
netG = Generator(nz, nc, ngf, ngpu).to(device)

if('cuda' in str(device)) and (ngpu > 1):
    netG = nn.DataParallel(netG, list(range(ngpu)))
    
netG.apply(weights_init)
print(netG)

# Create the discriminator.
netD = Discriminator(nz, nc, ndf, ngpu).to(device)

if('cuda' in str(device)) and (ngpu > 1):
    netD = nn.DataParallel(netD, list(range(ngpu)))

netD.apply(weights_init)
print(netD)

# Binary Cross Entropy loss function.
criterion = nn.BCELoss()

if(device.type == 'cuda'):
    netD.cuda()
    netG.cuda()
    criterion.cuda()

fixed_noise = torch.randn(64, nz, 1, 1, device=device)

real_label = 0.9
fake_label = 0

# Optimizer for the discriminator.
optimizerD = optim.Adam(netD.parameters(), lr=opt.lr, betas=(opt.beta1, 0.999))
# Optimizer for the generator.
optimizerG = optim.Adam(netG.parameters(), lr=opt.lr, betas=(opt.beta1, 0.999))

# Stores generated images as training progresses.
img_list = []
# Stores generator losses during training.
G_losses = []
# Stores discriminator losses during training.
D_losses = []

iters = 0
W = opt.imsize
H = opt.imsize

std = 0.1
#define noise
#noise = torch.FloatTensor(params['bsize'], params['nz'], 1, 1, 1)
#noise = Variable(noise)

#input = torch.FloatTensor(params['bsize'], params['nc'], params['imsize'], params['imsize'], params['imsize'])
#input = Variable(input)

#additive_noise = torch.FloatTensor(params['bsize'], params['nc'], params['imsize'], params['imsize'], params['imsize'])
#additive_noise = Variable(additive_noise)

print("Starting Training Loop...")
print("-"*25)

for epoch in range(opt.nepochs):
    for i, data in enumerate(dataloader, 0):
        ############################
        # (1) Update D network: maximise log(D(x)) + log(1 - D(G(z)))
        ###########################
        netD.zero_grad()
        
        #real_data = data[0].to(device)
        real_data = data.to(device)
        #print('real', real_data.shape)
        
        b_size = real_data.size(0)
        #print(b_size)
        
        label = torch.full((b_size,), real_label, device=device)
        
        output = netD(real_data).view(-1)
        #print(output.shape)
        errD_real = criterion(output, label)
        errD_real.backward()
        D_x = output.mean().item()
        
        noise = torch.randn(b_size, nz, 1, 1, 1, device=device)
        fake_data = netG(noise)
        label.data.fill_(fake_label)
        output = netD(fake_data.detach()).view(-1)
        errD_fake = criterion(output, label)
        errD_fake.backward()
        D_G_z1 = output.mean().item()
        errD = errD_real + errD_fake
        optimizerD.step()

        
        ############################
        # (2) Update G network: maximize log(D(G(z)))
        ###########################
        netG.zero_grad()
        label.data.fill_(real_label)
        noise = torch.randn(b_size, nz, 1, 1, 1, device=device)
        fake_data = netG(noise)
        #print(fake_data.shape)
        output = netD(fake_data).view(-1)
        errG = criterion(output,label)
        errG.backward()
        D_G_z2 = output.data.mean().item()
        optimizerG.step()
        
        iters += 1
                
        # Check progress of training.
        if i%50 == 0:
            print('[%d/%d][%d/%d]\tLoss_D: %.4f\tLoss_G: %.4f\tD(x): %.4f\tD(G(z)): %.4f / %.4f'
                  % (epoch, opt.nepochs, i, len(dataloader),
                     errD.item(), errG.item(), D_x, D_G_z1, D_G_z2))

        # Save the losses for plotting.
        G_losses.append(errG.item())
        D_losses.append(errD.item())

        
    if epoch % opt.save_epoch == 0:
        save_hdf5(fake_data.data, 'images_3D/fake_samples_{0}.hdf5'.format(iters))

    if epoch % opt.save_epoch == 0:    
        # Save checkpoints
        torch.save(netG.state_dict(), 'threephase_model/netG_epoch_{}.pth'.format(epoch))
        torch.save(netD.state_dict(), 'threephase_model/netD_epoch_{}.pth'.format(epoch))
        torch.save(optimizerG.state_dict(), 'threephase_model/optimG_epoch_{}.pth'.format(epoch))
        torch.save(optimizerD.state_dict(), 'threephase_model/optimD_epoch_{}.pth'.format(epoch))

# Save the final trained model
torch.save(netG.state_dict(), 'threephase_model/netG_final.pth'.format(epoch))
torch.save(netD.state_dict(), 'threephase_model/netD_final.pth'.format(epoch))
torch.save(optimizerG.state_dict(), 'threephase_model/optimG_final.pth'.format(epoch))
torch.save(optimizerD.state_dict(), 'threephase_model/optimD_final.pth'.format(epoch))

   