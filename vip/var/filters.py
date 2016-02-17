#! /usr/bin/env python

"""
Module with frame filtering funcions
"""

from __future__ import division

__author__ = 'C. Gomez @ ULg'
__all__ = ['frame_filter_highpass',
           'frame_filter_gaussian2d',
           'wavelet_denoise',
           'gaussian_kernel']

import pywt
import numpy as np
import photutils
from scipy.ndimage import gaussian_filter, median_filter      
from astropy.convolution import convolve_fft, Gaussian2DKernel
from astropy.stats import gaussian_fwhm_to_sigma
from .shapes import frame_center


def fft(array):
    """ Performs the 2d discrete Fourier transform (using numpy's fft2 function) 
    on the data from the original image. This produces a new representation of 
    the image in which each pixel represents a spatial frequency and 
    orientation, rather than an xy coordinate. When Fourier-transformed images 
    are plotted graphically, the low frequencies are found at the centre; this 
    is not what fft2 actually produces, so we need to also apply numpy's 
    fftshift.
    """
    fft_array = np.fft.fftshift(np.fft.fft2(array))
    return fft_array
    
def ifft(array):
    """ Gets the inverse Fourier transform on the image. This produces an array 
    of complex numbers whose absolute values correspond to the image in the 
    original space.
    """
    new_array = np.abs(np.fft.ifft2(np.fft.ifftshift(array)))
    return new_array

def frame_filter_highpass(array, mode, median_size=5, kernel_size=5, 
                          fwhm_size=5):
    """ High-pass filtering of input frame depending on parameter *mode*. The
    results are very different with different *mode* and varying the rest of
    parameters.
    
    Parameters
    ----------
    array : array_like
        Input array, 2d frame.
    mode : {''}
    median_size : int
        Size of the median box for filtering the low-pass image.
    kernel_size : 3 or 5
        Size of the Laplacian kernel for convolution. 
    fwhm_size : 
    
    Returns
    -------
    filtered : array_like
        High-pass filtered image.
        
    """
    if not array.ndim==2:
        raise TypeError('Input array is not a frame or 2d array')
    
    if mode=='kernel-conv':
        # Performs convolution of the frame with a 3x3 or 5x5 Laplacian 
        # high-pass kernels. 
        kernel3 = np.array([[-1, -1, -1], # A simple and very narrow highpass filter
                            [-1,  8, -1],
                            [-1, -1, -1]])
        #kernel3 = np.array([[0,  -1,  0],
        #                    [-1, 4, -1],
        #                    [0, -1,  0]])
        #kernel3 = np.array([[-0.17, -0.67, -0.17],
        #                    [-0.67, 3.33, -0.67],
        #                    [-0.17, -0.67, -0.17]])
        kernel5 = np.array([[-1, -1, -1, -1, -1],
                            [-1,  1,  2,  1, -1],
                            [-1,  2,  4,  2, -1],
                            [-1,  1,  2,  1, -1],
                            [-1, -1, -1, -1, -1]])
        if kernel_size==3:  kernel = kernel3
        elif kernel_size==5:  kernel = kernel5
        filtered = convolve_fft(array, kernel)
    
    elif mode=='median-subt':
        # Subtracting the low_pass filtered (median) image from the image itself  
        medianed = median_filter(array, median_size, mode='nearest')
        filtered = array - medianed
    
    elif mode=='gauss-subt':
        # Subtracting the low_pass filtered (median) image from the image itself  
        gaussed = frame_filter_gaussian2d(array, fwhm_size, mode='conv')
        filtered = array - gaussed
        
    elif mode=='fourier-butter':
        # Designs an n-th order high-pass 2D Butterworth filter with cutin
        # frequency f. pxd defines the number of pixels per unit of frequency 
        # (e.g.,degrees of visual angle).
        f = 0.5
        pxd = float(2)
        n = 100
        rows, cols = array.shape
        x = np.linspace(-0.5, 0.5, cols)  * cols / pxd
        y = np.linspace(-0.5, 0.5, rows)  * rows / pxd
        radius = np.sqrt((x**2)[np.newaxis] + (y**2)[:, np.newaxis])
        filt = 1 / (1.0 + (radius / f)**(2*n))
        filt = 1. - filt
        array_fft = fft(array)
        fft_new = array_fft * filt
        filtered = ifft(fft_new)        
        
    else:
        raise TypeError('Mode not recognized')    
        
    return filtered



def frame_filter_gaussian2d(array, size_fwhm, mode='conv'):
    """ 2d Gaussian filter. 
    
    Parameters
    ----------
    array : array_like
        Input array, 2d frame.
    size_fwhm : float
        Size in pixels of the FWHM of the gaussian kernel.
    mode : {'conv', 'convfft'}
        'conv' uses the multidimensional gaussian filter from scipy.ndimage and
        'convfft' uses the fft convolution with a 2d Gaussian kernel.
        
    Returns
    -------
    filtered : array_like
        Convolved image.
        
    """
    if not array.ndim==2:
        raise TypeError('Input array is not a frame or 2d array')
    
    if mode=='conv':
        filtered = gaussian_filter(array, sigma=size_fwhm*gaussian_fwhm_to_sigma, 
                                   order=0, mode='nearest')
    elif mode=='convfft':
        # FFT Convolution with a 2d gaussian kernel created with Astropy.
        gaus = Gaussian2DKernel(stddev=size_fwhm*gaussian_fwhm_to_sigma)
        filtered = convolve_fft(array, gaus)
    else:
        raise TypeError('Mode not recognized')
    
    return filtered



def wavelet_denoise(array, wavelet, threshold, levels, thrmode='hard'):
    """ Wavelet filtering of a 2d array using Pywt library. First a 2d discrete
    wavelet transform is performed followed by a hard or soft thresholding of 
    the coefficients.
    
    Parameters
    ----------
    array : array_like
        Input 2d array or image.
    wavelet : Pywt wavelet object
        Pywt wavelet object. Example: pywt.Wavelet('bior2.2')
    threshold : int
        Threshold on the wavelet coefficients.
    levels : int
        Wavelet levels to be used.
    thrmode : {'hard','soft'}, optional
        Mode of thresholding of the wavelet coefficients.
    
    Returns
    -------
    array_filtered : array_like
        Filtered array with the same dimensions and size of the input one. 
    
    Notes
    -----
    Full documentation of the PyWavelets package here:
    http://www.pybytes.com/pywavelets/
    
    For information on the builtin wavelets and how to use them:
    http://www.pybytes.com/pywavelets/regression/wavelet.html
    http://wavelets.pybytes.com
    
    """
    if not array.ndim==2:
        raise TypeError('Input array is not a frame or 2d array')
    
    WC = pywt.wavedec2(array, wavelet, level=levels)
    if thrmode=='hard':
        NWC = map(lambda x: pywt.thresholding.hard(x, threshold), WC)
    elif thrmode=='soft':
        NWC = map(lambda x: pywt.thresholding.soft(x, threshold), WC)
    else:
        raise ValueError('Threshold mode not recognized')
    array_filtered = pywt.waverec2(NWC, wavelet)
    
    return array_filtered

   
    
def gaussian_kernel(size, size_y=None):
    """ Gaussian kernel.
    """
    size = int(size)
    if not size_y:
        size_y = size
    else:
        size_y = int(size_y)
    x, y = np.mgrid[-size:size+1, -size_y:size_y+1]
    g = np.exp(-(x**2/float(size)+y**2/float(size_y)))

    fwhm = size
    fwhm_aper = photutils.CircularAperture((frame_center(g)), fwhm/2.)
    fwhm_aper_phot = photutils.aperture_photometry(g, fwhm_aper)
    g_norm = g/np.array(fwhm_aper_phot['aperture_sum'])
     
    return g_norm/g_norm.max()



