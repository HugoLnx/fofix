# -*- coding: utf-8 -*-
#####################################################################
#                                                                   #
# Frets on Fire X (FoFiX)                                           #
# Copyright (C) 2009-2010 FoFiX Team                                #
# See CREDITS for a full list of contributors                       #
#                                                                   #
# This program is free software; you can redistribute it and/or     #
# modify it under the terms of the GNU General Public License       #
# as published by the Free Software Foundation; either version 2    #
# of the License, or (at your option) any later version.            #
#                                                                   #
# This program is distributed in the hope that it will be useful,   #
# but WITHOUT ANY WARRANTY; without even the implied warranty of    #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the     #
# GNU General Public License for more details.                      #
#                                                                   #
# You should have received a copy of the GNU General Public License #
# along with this program; if not, write to the Free Software       #
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,        #
# MA  02110-1301, USA.                                              #
#####################################################################
from __future__ import with_statement
from OpenGL.GL import *

import numpy as np
from numpy import array, float32
import math
from cmgl import *

import Log
from Texture import Texture
from PIL import Image

#stump: the last few stubs of DummyAmanith.py are inlined here since this
# is the only place in the whole program that uses it now that we've pruned
# the dead SVG code.
class SvgContext(object):
  def __init__(self, geometry):
    self.geometry = geometry
    self.transform = SvgTransform()
    self.setGeometry(geometry)
    self.setProjection(geometry)
    glMatrixMode(GL_MODELVIEW)
  
  def setGeometry(self, geometry = None):
    glViewport(geometry[0], geometry[1], geometry[2], geometry[3])
    glScalef(geometry[2] / 640.0, geometry[3] / 480.0, 1.0)

  def setProjection(self, geometry = None):
    geometry = geometry or self.geometry
    with cmglMatrixMode(GL_PROJECTION):
      glLoadIdentity()
      glOrtho(geometry[0], geometry[0] + geometry[2], geometry[1], geometry[1] + geometry[3], -100, 100)
    self.geometry = geometry

  def clear(self, r = 0, g = 0, b = 0, a = 0):
    glDepthMask(1)
    glEnable(GL_COLOR_MATERIAL)
    glClearColor(r, g, b, a)
    glClear(GL_COLOR_BUFFER_BIT | GL_STENCIL_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


class SvgTransform(object):
  def __init__(self, baseTransform = None):
    self.reset()
    if baseTransform is not None:
      self.ops = baseTransform.ops[:]

  def transform(self, transform):
    self.ops.extend(transform.ops)

  def reset(self):
    self.ops = []

  def translate(self, dx, dy):
    # The old code did this with a matrix addition, not a multiplication.
    # We get the same effect by doing the translations before anything else.
    self.ops.insert(0, lambda: glTranslatef(dx, dy, 0))

  def rotate(self, angle):
    self.ops.append(lambda: glRotatef(math.degrees(angle), 0.0, 0.0, 1.0))

  def scale(self, sx, sy):
    self.ops.append(lambda: glScalef(sx, sy, 1.0))

  def applyGL(self):
    for op in self.ops:
      op()


class ImgDrawing(object):
  def __init__(self, context, ImgData):
    self.ImgData = None
    self.texture = None
    self.context = context
    self.cache = None
    self.filename = ImgData

    # Detect the type of data passed in
    if type(ImgData) == file:
      self.ImgData = ImgData.read()
    elif type(ImgData) == str:
      self.texture = Texture(ImgData)
    elif isinstance(ImgData, Image.Image): #stump: let a PIL image be passed in
      self.texture = Texture()
      self.texture.loadImage(ImgData)

    # Make sure we have a valid texture
    if not self.texture:
      if type(ImgData) == str:
        e = "Unable to load texture for %s." % ImgData
      else:
        e = "Unable to load texture for SVG file."
      Log.error(e)
      raise RuntimeError(e)

    self.pixelSize = self.texture.pixelSize
    self.position = [0.0,0.0]
    self.scale    = [1.0,1.0]
    self.angle    = 0
    self.color    = (1.0,1.0,1.0)
    self.rect     = (0,1,0,1)
    self.shift    = -.5

    self.createArrays()

  def createArrays(self):
    self.vtxArray = np.zeros((4,2), dtype=float32)
    self.texArray = np.zeros((4,2), dtype=float32)

    self.createVtx()
    self.createTex()

  def createVtx(self):
    vA = self.vtxArray #short hand variable casting
    
    #topLeft, topRight, bottomRight, bottomLeft
    vA[0,0] = 0.0; vA[0,1] = 1.0
    vA[1,0] = 1.0; vA[1,1] = 1.0
    vA[2,0] = 1.0; vA[2,1] = 0.0
    vA[3,0] = 0.0; vA[3,1] = 0.0
    
  def createTex(self):
    tA = self.texArray
    rect = self.rect

    #topLeft, topRight, bottomRight, bottomLeft
    tA[0,0] = rect[0]; tA[0,1] = rect[3]
    tA[1,0] = rect[1]; tA[1,1] = rect[3]
    tA[2,0] = rect[1]; tA[2,1] = rect[2]
    tA[3,0] = rect[0]; tA[3,1] = rect[2]
    
  def width1(self):
    width = self.pixelSize[0]
    if width:
      return width
    else:
      return 0

  #myfingershurt:
  def height1(self):
    height = self.pixelSize[1]
    if height:
      return height
    else:
      return 0

  def widthf(self, pixelw):
    width = self.pixelSize[0]
    if width:
      wfactor = pixelw/width
      return wfactor
    else:
      return 0    

  def setPosition(self, x, y):
    self.position = [x,y]

  def setScale(self, width, height):
    self.scale = [width, height]

  def setAngle(self, angle):
    self.angle = angle

  def setRect(self, rect):
    if not rect == self.rect: 
      self.rect = rect
      self.createTex()

  def setAlignment(self, alignment):
    if alignment == 0:  #left
      self.shift = 0
    elif alignment == 1:#center
      self.shift = -.5
    elif alignment == 2:#right
      self.shift = -1.0

  def setColor(self, color):
    if len(color) == 3:
      color = (color[0], color[1], color[2], 1.0)
    self.color = color

  def draw(self):
    with cmglPushedSpecificMatrix(GL_TEXTURE):
      with cmglPushedSpecificMatrix(GL_PROJECTION):

        with cmglMatrixMode(GL_PROJECTION):
          self.context.setProjection()

        with cmglPushedMatrix():
          glLoadIdentity()

          glTranslate(self.position[0], self.position[1], 0.0)
          glScalef(self.scale[0], self.scale[1], 1.0)
          glRotatef(self.angle, 0, 0, 1)

          glScalef(self.pixelSize[0], self.pixelSize[1], 1)
          glTranslatef(self.shift, -.5, 0)
          glColor4f(*self.color)

          glEnable(GL_TEXTURE_2D)
          self.texture.bind()
          cmglDrawArrays(GL_QUADS, vertices=self.vtxArray, texcoords=self.texArray)
          glDisable(GL_TEXTURE_2D)
