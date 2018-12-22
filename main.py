import sys, os, math
import numpy as np
from collections import Counter
import time
try: # Pillow
  from PIL import Image
except:
  print ('Error: Pillow has not been installed.')
  sys.exit(0)

try: # PyOpenGL
  from OpenGL.GLUT import *
  from OpenGL.GL import *
  from OpenGL.GLU import *
except:
  print ('Error: PyOpenGL has not been installed.')
  sys.exit(0)



# Globals

localHistoRadius = 5  # distance within which to apply local histogram equalization
global mouse_button
# Select image
imgDir      = 'images'
imgFilename = 'mandrill.png'

#The image that is displayed in the window
currentImage = Image.open( os.path.join( imgDir, imgFilename ) ).convert( 'YCbCr' ).transpose( Image.FLIP_TOP_BOTTOM )
#The image transformed from originalImage, the source (full version) of currentImage.
tempImage    = None
#The same as currentImage, this allows multiple operations to be performed without loosing information from the original picture
originalImage = Image.open( os.path.join( imgDir, imgFilename ) ).convert( 'YCbCr' ).transpose( Image.FLIP_TOP_BOTTOM )
#The sclaing factor of last scaling operation (relative to the very original image)
lastFactor = 1

windowWidth  = currentImage.size[0] # window dimensions
windowHeight =  currentImage.size[1]
# File dialog (doesn't work on Mac OSX)

if sys.platform != 'darwin':
  import tkinter,tkinter.filedialog
  root = tkinter.Tk()
  root.withdraw()



# Apply brightness and contrast to tempImage and store in
# currentImage.

def applyBrightnessAndContrast( brightness, contrast ):

  width  = currentImage.size[0]
  height = currentImage.size[1]

  srcPixels = tempImage.load()
  dstPixels = currentImage.load()

  contrast = contrast - 1 #convert values in range 0-1 to negative floats as the coefficient for decreasing contrast
  contrast = contrast * 2
  for i in range(width):
    for j in range(height):
      y, cb, cr = srcPixels[i, j]

      y = int(y +brightness * y/300)
      cb = int(min(255,(max(0,cb+(cb-128)*contrast))))
      cr = int(min(255,(max(0,cr+(cr-128)*contrast))))

      dstPixels[i, j] = (y,cb,cr)

  print ('adjust brightness = %f, contrast = %f' % (brightness,contrast))



# Perform local histogram equalization on the current image using the given radius.

def performHistoEqualization( radius ):

  pixels = currentImage.load()
  width  = currentImage.size[0]
  height = currentImage.size[1]
  tempPixels = currentImage.copy().load()

  # iterate through the  image
  for x in range(0, width):
    for y in range(0, height):
      thisPixel = tempPixels[x, y]
      totalNumberOfPixels = 0 # total number of pixels
      pixelCountToTheLeft = 0 # counter of the number of pixels to the left of the center pixel on a histogram
      # select pixels that's darker than the current one,with in 2 cartesian distance
      for i in range(-radius, radius + 1):
        if (x+i<0 or x+i>=width):
          continue
        totalNumberOfPixels = totalNumberOfPixels+1
        for j in range(-radius, radius + 1):
          if (y+j<0 or y+j>=height):
            continue
          totalNumberOfPixels = totalNumberOfPixels + 1
          if tempPixels[x + i, y + j][0] <= thisPixel[0]:  # compare Y value
            pixelCountToTheLeft = pixelCountToTheLeft + 1
      newY = (256 / totalNumberOfPixels) * pixelCountToTheLeft - 1  # equalize the value of histogram
      pixels[x, y] = (int(newY), thisPixel[1], thisPixel[2])

  print ('perform local histogram equalization with radius %d' % radius)



# Scale the tempImage by the given factor and store it in
# currentImage. Use backward projection.  This is called when the
# mouse is moved with the right button held down.

def scaleImage( factor ):
  global lastFactor,calculationTime
  factor = factor * lastFactor

  width  = currentImage.size[0]
  height = currentImage.size[1]

  srcPixels = originalImage.load() # always load the original image to preserve pixels
  dstPixels = currentImage.load()

  inverseT = np.array([[1 / factor, 0], [0, 1 / factor]]) # calculate the inverse matrix

  for i in range(width):
    for j in range(height):
        [x,y] = inverseT.dot([i, j]) # back projection

        #consider only pixels within the size of the original image
        if (x<=width and y<=height):
          pixelValue = () #initialize the new pixelValue

          # scaling down
          if (factor<1):
            pixelValue = srcPixels[int(x), int(y)]
          #scaling up
          else:
            xFloor = int(x);
            yFloor = int(y);
            alpha = x - xFloor;
            beta = y - yFloor;

            ############################### scaling up using bilinear interpolation (disabled by default) #################################
            usebilinear = False # you can see the result of bilinear interpolation if you change the boolean value of this to true
            if usebilinear:
              if (xFloor >= 0 and yFloor >=0 and xFloor+1<width and yFloor+1<height):#pixels inside the image edge
                srcP = np.array((srcPixels[xFloor, yFloor], srcPixels[xFloor + 1, yFloor], srcPixels[xFloor, yFloor + 1],
                                srcPixels[xFloor + 1, yFloor + 1])) # collections of pixels
                srcW = np.array(([(1 - alpha) * (1 - beta), alpha * (1 - beta), (1 - alpha) * beta, alpha * beta])) #collection of weights based on overlay area
                pixelValue = tuple(np.dot(srcW,srcP).astype(int)) # adding up  (collection of pixels) * (collection  of weights)
              else:#pixels at the edge of the image
                pixelValue = srcPixels[int(x),int(y)]

            ############################### scaling up without interpolation #################################
            else:#use back projection without bilinear interpolation
              pixelValue = srcPixels[int(x), int(y)]

          dstPixels[i,j] = pixelValue

        #replace extra pixels with white pixels (for scaling down)
        else:
          dstPixels[i,j] = (255,128,128)

  print ('scale image by %f' % (factor/lastFactor))
  lastFactor = factor


# Set up the display and draw the current image

def display():

  # Clear window

  glClearColor ( 1, 1, 1, 0 )
  glClear( GL_COLOR_BUFFER_BIT )

  # rebuild the image

  img = currentImage.convert( 'RGB' )

  width  = img.size[0]
  height = img.size[1]

  # Find where to position lower-left corner of image

  baseX = (windowWidth-width)/2
  baseY = (windowHeight-height)/2

  glWindowPos2i(int(baseX), int(baseY))

  # Get pixels and draw

  imageData = np.array( list( img.getdata() ), np.uint8 )

  glDrawPixels( width, height, GL_RGB, GL_UNSIGNED_BYTE, imageData )

  glutSwapBuffers()



# Handle keyboard input

def keyboard( key, x, y ):

  global localHistoRadius
  print(key)
  if key == '\033' or key == b'\x1b': # ESC = exit
    #print("pressed 'esc'")
    sys.exit(0)
      
  elif key == 'l' or key == b'l':
    #print("pressed 'l'")
    if sys.platform != 'darwin':
      path = tkFileDialog.askopenfilename( initialdir = imgDir )
      if path:
        loadImage( path )

  elif key == 's'or key == b's':
    #print("pressed 's'")
    if sys.platform != 'darwin':
      outputPath = tkFileDialog.asksaveasfilename( initialdir = '.' )
      if outputPath:
        saveImage( outputPath )

  elif key == 'h' or key == b'h':
    #print("pressed 'h'")
    performHistoEqualization( localHistoRadius )

  elif key in ['+','=',b'+',b'=']:
    #print("pressed '+='")
    localHistoRadius = localHistoRadius + 1
    print ('radius =', localHistoRadius)

  elif key in ['-','_',b'-',b'_']:
    #print("pressed '_-'")
    localHistoRadius = localHistoRadius - 1
    if localHistoRadius < 1:
      localHistoRadius = 1
    print ('radius =', localHistoRadius)

  else:
    print ('key =', key)    

  glutPostRedisplay()



# Load and save images.
#
# Modify these to load to the current image and to save the current image.
#


def loadImage( path ):

  global currentImage

  currentImage = Image.open( path ).convert( 'YCbCr' ).transpose( Image.FLIP_TOP_BOTTOM )


def saveImage( path ):

  global currentImage

  currentImage.transpose( Image.FLIP_TOP_BOTTOM ).convert('RGB').save( path )



# Handle window reshape


def reshape( newWidth, newHeight ):

  global windowWidth, windowHeight

  windowWidth  = newWidth
  windowHeight = newHeight

  glutPostRedisplay()



# Mouse state on initial click

button = None
initX = 0
initY = 0



# Handle mouse click/release

def mouse( btn, state, x, y ):
  global button, initX, initY, tempImage

  if state == GLUT_DOWN:
    tempImage = currentImage.copy()
    button = btn
    initX = x
    initY = y
  elif state == GLUT_UP:
    if btn == GLUT_RIGHT_BUTTON:
      initPosX = initX - float(windowWidth) / 2.0
      initPosY = initY - float(windowHeight) / 2.0
      initDist = math.sqrt(initPosX * initPosX + initPosY * initPosY)
      if initDist == 0:
        initDist = 1
      newPosX = x - float(windowWidth) / 2.0
      newPosY = y - float(windowHeight) / 2.0
      newDist = math.sqrt(newPosX * newPosX + newPosY * newPosY)
      scaleImage(newDist / initDist)
    else:
      tempImage = None
      button = None

  glutPostRedisplay()



# Handle mouse motion

def motion( x, y ):

  if button == GLUT_LEFT_BUTTON:
    diffX = x - initX
    diffY = y - initY

    applyBrightnessAndContrast( 255 * diffX/float(windowWidth), 1 + diffY/float(windowHeight) )

  elif button == GLUT_RIGHT_BUTTON:
    pass # these codes are copied to mouse becuase the motion function would be called multiple times when the cursor keeps
         # moving when hold theh right button down which makes the scaling very laggy
  glutPostRedisplay()



# Run OpenGL

glutInit()
glutInitDisplayMode( GLUT_DOUBLE | GLUT_RGB )
glutInitWindowSize( windowWidth, windowHeight )
glutInitWindowPosition( 1, 1 )

glutCreateWindow( 'imaging' )

glutDisplayFunc( display )

glutKeyboardFunc( keyboard )
glutReshapeFunc( reshape )
glutMouseFunc( mouse )
glutMotionFunc( motion )

glutMainLoop()

