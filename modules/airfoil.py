#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

    Airfoil and operations on it 

"""
import os
import numpy as np
from math_util import * 
from common_utils import * 
from spline_of_airfoil import SideOfAirfoil, SplineOfAirfoil



class Airfoil:
    """ 

    Airfoil object to handle a airfoil direct related things  

    """
    isStrakAirfoil      = False
    isEdited            = False
    isExample           = False                      # vs. Example_Airfoil 

    def __init__(self, x= None, y = None, pathFileName = None, name = None, workingDir= None):
        """
        Main constructor for new Airfoil

        Args:
            :pathFileName: optional - string of existinng airfoil path and name \n
            :name: optional - name of airfoil - no checks performed 
            :x,y: optional - the coordinates of airfoil 
        """

        self.pathFileName = None
        self.workingDir   = workingDir if workingDir is not None else ''
        self._name        = name if name is not None else ''
        self.sourceName   = None                 # long name out of the two blended airfoils (TSrakAirfoil)

        self._x              = x                 # x-coordinates 
        self._y              = y                 # y-coordinates
        self._iLe            = None              # index of leading edge          
        self._isModified     = False
        self._isEdited       = False 
        self._isStrakAirfoil = False             # is self blended from two other airfoils 

        self._spline         = None              # 2D spline object 

        self._nPanelsNew     = 200               # repanel: no of panels 
        self._le_bunch       = 0.84              # repanel: panel bunch at leading edge
        self._te_bunch       = 0.7   	         # repanel: panel bunch at trailing edge


        if (pathFileName is not None): 
            if os.path.isabs (pathFileName):
                checkPath = pathFileName
            else:
                checkPath = os.path.join (self.workingDir, pathFileName)
            if not os.path.isfile(checkPath):
                ErrorMsg ("Airfoil file \'%s\' does not exist. Couldn\'t create Airfoil" % checkPath)
                self._name = "-- ? --"
            else:
                self.pathFileName = pathFileName
                self._name = os.path.splitext(os.path.basename(self.pathFileName))[0]  # load will get the real name
        elif (not name):
            self._name = "-- ? --"


    @classmethod
    def onDict(cls, dataDict, workingDir = None):
        """
        Alternate constructor for new Airfoil based on dictionary 

        Args:
            :dataDict: dictionary with "name" and "file" keys
            :workingDir: home of dictionary (paramter file) 
        """
        pathFileName  = fromDict(dataDict, "file", None)
        name          = fromDict(dataDict, "name", None)
        return cls(pathFileName = pathFileName, name = name, workingDir=workingDir)
    

    @classmethod
    def asCopy (cls, sourceAirfoil: 'Airfoil', nameExt="-mod"):
        """
        Alternate constructor for new Airfoil based on another airfoil  

        Args:
            :sourceAirfoil: the source airfoil to copy
            :nameExt: will be appended to the source aifoil name
        """
        name = sourceAirfoil.name + nameExt
        x = np.copy (sourceAirfoil.x)               # initial coordinates
        y = np.copy (sourceAirfoil.y)

        return cls(x = x, y = y, name = name )



    def _save (self, airfoilDict):
        """ stores the variables into the dataDict - returns the filled dict"""
        
        if self.isStrakAirfoil:
            toDict (airfoilDict, "name", self.name) 
        else:
            toDict (airfoilDict, "file", self.pathFileName) 
        return airfoilDict
 

    def __repr__(self) -> str:
        # overwrite to get a nice print string 
        info = f"\'{self.name}\'"
        return f"{type(self).__name__} {info}"


    # ----------  Properties ---------------

    @property
    def x (self): return self._x

    @property
    def y (self): return self._y

    def set_xy (self, newX, newY): 
        self._x      = newX
        self._y      = newY
        self._iLe    = None
        self._spline = None
        self.set_isModified (True)
  
    @property
    def name (self): return self._name 
    def set_name (self, newName):
        """  Set der name of the airfoil 
        Note:  This will not rename an existing airfoil (file). Use rename instead...
        """
        self._name = newName
        self.set_isModified (True)

    @property
    def isEdited (self): return self._isModified
    """ True if airfoil is being edited, modifiied, ..."""
        # cuurently equals to isModified ...
    def set_isEdited (self, aBool): 
        self.set_isModified (aBool) 


    @property
    def isModified (self): return self._isModified
    """ True if airfoil is being modifiied, ..."""
    def set_isModified (self, aBool): 
        self._isModified = aBool 

    @property
    def isExisting (self):
        return not self.pathFileName is None


    @property
    def isLoaded (self):
        return self._x is not None and len(self._x) > 10
    
    @property
    def isNormalized (self):
        """ is LE at 0,0 and TE at 1,.. ?"""
        if self._x is None: return False

        xteUp, yteUp, xteLow, yteLow = self.te_fromPoints
        if xteUp != 1.0 or xteLow != 1.0: return False
        if yteUp != - yteLow: return False
        xle, yle = self.le 
        if xle != 0.0 or yle != 0.0: return False
        return True
    
    @property
    def isNormalized_HighPrec (self):
        """ is LE at 0,0 and TE at 1,.. and also LE of spline at 0,0 ?"""
        return self.spline.isNormalized


    @property
    def isStrakAirfoil (self):
        """ is self blended out of two other airfoils"""
        return self._isStrakAirfoil
    def set_isStrakAirfoil (self, aBool): 
        self._isStrakAirfoil = aBool
    
    @property
    def iLe (self) -> int: 
        """ the index of leading edge in x coordinate array"""
        if self._iLe is None:
            self._iLe = int(np.argmin (self._x))
        return self._iLe

    @property
    def le (self): 
        """ returns leading edge x,y of point coordinate data """
        return self._x[self.iLe], self._y[self.iLe]


    @property
    def te_fromPoints (self): 
        """ returns trailing edge upper and lower x,y of point coordinate data """
        return self._x[0], self._y[0], self._x[-1], self._y[-1]
    
    @property
    def nPanels (self): 
        """ number of panels """
        return len (self._x)  - 1
      
    @property
    def nPoints (self): 
        """ number of coordinate points"""
        return len (self._x)

    @property 
    def panelAngle_le (self): 
        """returns the panel angle of the 2 panels at leading edge - should be less 170"""

        # panang1 = atan((zt(2)-zt(1))/(xt(2)-xt(1))) *                &
        #           180.d0/acos(-1.d0)
        # panang2 = atan((zb(1)-zb(2))/(xb(2)-xb(1))) *                &
        #           180.d0/acos(-1.d0)
        # maxpanang = max(panang2,panang1)
        ile = self.iLe
        dx = self.x[ile-1] - self.x[ile]
        dy = self.y[ile-1] - self.y[ile]
        if dx > 0.0:
            angleUp = math.atan (dy/dx) * 180.0 / math.acos(-1)
        else: 
            angleUp = 90 

        dx = self.x[ile+1] - self.x[ile]
        dy = self.y[ile] - self.y[ile+1]
        if dx > 0.0:
            angleLo = math.atan (dy/dx) * 180.0 / math.acos(-1)
        else: 
            angleLo = 90 

        if angleUp < 90.0 and angleLo < 90.0: 
            angle = angleUp + angleLo           # total angle 
        else: 
            angle = 180.0                       # pathologic case with vertical le panel
        return angle 

    @property
    def panelAngle_min (self): 
        """ returns the min angle between two panels - something between 160-180° - 
        and the point index of the min point"""
        return np.min(panel_angles(self.x,self.y)),  np.argmin(panel_angles(self.x,self.y))       


    @property
    def teGap (self): 
        """ trailing edge gap in %"""
        return  (self.y[0] - self.y[-1]) * 100
    def set_teGap (self, newGap): 
        """ set trailing edge gap to new value which is in %"""
        newGap = max(0.0, newGap)
        newGap = min(5.0, newGap)
        self.set_xy(*self.with_TEGap( newGap / 100))
        

    @property
    def maxThickness (self): 
        """ max thickness in %"""
        return self.spline.maxThick * 100
    def set_maxThickness(self,newVal): 
        """ set max thickness in %"""

        # do not allow thickness < 0,5% 
        if newVal < 0.5: newVal = 0.5

        self.spline.set_maxThick (newVal/100.0)
        self.set_xy (self.spline.x, self.spline.y)


    @property
    def maxThicknessX (self): 
        """ max thickness x-position in %"""
        return self.spline.maxThickX * 100
    def set_maxThicknessX(self,newVal): 
        """ set max thickness x-position in %"""
        self.spline.set_maxThickX (newVal/100.0)
        self.set_xy (self.spline.x, self.spline.y)


    @property
    def maxCamber (self): 
        """ max camber in %"""
        return self.spline.maxCamb * 100
    def set_maxCamber(self,newVal): 
        """ set max camber in %"""
        self.spline.set_maxCamb (newVal/100.0)
        self.set_xy (self.spline.x, self.spline.y)


    @property
    def maxCamberX (self): 
        """ max camber x-position in %"""
        return self.spline.maxCambX * 100
    def set_maxCamberX(self,newVal): 
        """ set max camber x-position in %"""
        self.spline.set_maxCambX (newVal/100.0)
        self.set_xy (self.spline.x, self.spline.y)

    @property
    def isSymmetric(self):
        """ true if max camber is 0.0 - so it's a symmetric airfoil"""
        return self.spline.maxCamb == 0.0


    @property
    def camber (self) -> 'SideOfAirfoil': 
        """ camber line as Line object"""
        return self.spline.camber 

    @property
    def thickness (self) -> 'SideOfAirfoil': 
        """ thickness distribution as Line object """
        return self.spline.thickness

    @property 
    def spline (self) -> SplineOfAirfoil:
        """ spline representation  of self - to show curvature, etc. """

        if self._spline is None: 
            self._spline = SplineOfAirfoil (self.x, self.y)
        return self._spline


    @property
    def upper(self) -> SideOfAirfoil: 
        """returns the upper surface as a line object - where x 0..1"""
        if self.isLoaded:
            return SideOfAirfoil(np.flip (self._x [0: self.iLe + 1]), np.flip (self._y [0: self.iLe + 1]), name='upper')
        else: 
            return None
            
    @property
    def lower(self) -> SideOfAirfoil: 
        """returns the lower surface as a line object - where x 0..1"""
        if self.isLoaded:
            return SideOfAirfoil(self._x[self.iLe:], self._y[self.iLe:], name='lower')
        else: 
            return None


    @property
    def nPanelsNew (self): 
        """ number of panels when being repaneled"""
        return self._nPanelsNew
    def set_nPanelsNew (self, newVal): 
        """ set number of panels and repanel"""
        newVal = int (newVal / 2) * 2           # must be even 
        newVal = max (40,  newVal)
        newVal = min (500, newVal) 
        self._nPanelsNew = int (newVal)
        self.repanel()

    @property
    def le_bunch (self): 
        """ leading edge bunch of panels"""
        return self._le_bunch
    def set_le_bunch (self, newVal): 
        """ set leading edge bunch of panels and repanel"""
        self._le_bunch = newVal
        self.repanel()

    @property
    def te_bunch (self): 
        """ trailing edge bunch of panels"""
        return self._te_bunch
    def set_te_bunch (self, newVal): 
        """ set trailing edge bunch of panels and repanel"""
        self._te_bunch = newVal
        self.repanel()


    #-----------------------------------------------------------


    def set_pathFileName (self,fullPath):
        """
        Set der fullpaths of airfoils location and file \n
        ! This will not move or copy the airfoil physically - use clone instead

        Args:
            :newName: String like '..\myAirfoils\JX-GT-15.dat'
        """

        if (os.path.isfile(fullPath)):
            self.pathFileName = fullPath
        else:
            ErrorMsg ("Airfoil \'%s\' does not exist. Couldn\'t be set" % fullPath)

    @property
    def fileName (self):
        """
        Get filename of airfoil 

        Returns: 
            String like 'JX-GT-15.dat'
        """
        if not self.pathFileName is None: 
            return os.path.basename(self.pathFileName) 
        else:
            return None

        

    def load (self, fromPath = None):
        """
        Loads airfoil coordinates from file. 
        pathFileName must be set before or fromPath must be defined.
        Load doesn't change self pathFileName
        """    

        if fromPath and os.path.isfile (fromPath):
            sourcePathFile = fromPath
        elif self.isExisting and not self.isLoaded: 
            sourcePathFile = os.path.join(self.workingDir, self.pathFileName)
        else:
            sourcePathFile = None 

        if sourcePathFile:
            f = open(sourcePathFile, 'r')
            file_lines = f.readlines()
            f.close()
            self._loadLines(file_lines)


    def _loadLines (self, file_lines):
        # read the lines of the airfoil file into self x,y

        x = []
        y = []
        xvalPrev = -9999.9
        yvalPrev = -9999.9

        for i, line in enumerate(file_lines):
            if (i > 0): 
                splitline = line.strip().split(" ",1)
                if len(splitline) == 1:                        # couldn't split line - try tab as separator
                    splitline = line.strip().split("\t",1)
                if len(splitline) >= 2:                     
                    xval = float(splitline[0].strip())
                    yval = float(splitline[1].strip())
                    if xval == xvalPrev and yval == yvalPrev:   # avoid duplicate, dirty coordinates
                        WarningMsg ("Airfoil '%s' has duplicate coordinates - skipped." % self._name)
                    else: 
                        x.append (xval)
                        y.append (yval) 
                    xvalPrev = xval 
                    yvalPrev = yval 
            else: 
                self._name = line.strip()
        self._x = np.asarray (x)
        self._y = np.asarray (y)


    def saveAs (self, dir = None, destName = None):
        """
        save self to to destPath and destName and set new values to self
        if both destPath and name are not set, it's just a save to current directory
        """        
        newPathFileName = self.copyAs (dir, destName)
        self.pathFileName =  newPathFileName
        if destName: 
            self.set_name (destName)
        self.set_isModified (False)


    def copyAs (self, dir = None, destName = None, teGap=None ):
        """
        Write a copy of self to destPath and destName (the airfoil can be renamed).
        Self remains with its current values.
        Optionally a new teGap may be defined for the exported airfoil  
        return: 
            newPathFileName from dir and destName 
        """        

        # adjust te gap if requested
        if teGap is not None: 
            x, y = self.with_TEGap (teGap)
            if x is None:                                       # error - couldn't set new teGap 
                teGap = None 
        if teGap is None:  
            x = self.x
            y = self.y 
            teText = ''
        else: 
            teText = '_te=%.2f' % (teGap * 100)                 # te thickness in percent

        # determine (new) airfoils name 
        if not destName:
            if self.isStrakAirfoil:
                destName = self.sourceName                     # strak: take the long name of the two airfoils
            else:
                destName = self.name    
        destName = destName + teText   

        # create dir if not exist - build airfoil filename
        if dir: 
            if not os.path.isdir (dir):
                os.mkdir(dir)
            newPathFileName = os.path.join (dir, destName) + '.dat'
        else: 
            newPathFileName = destName + '.dat'

        # write header and coordinates
        with open(newPathFileName, 'w+') as file:
            file.write("%s\n" % destName)
            for i in range (len(x)):
                file.write("%.7f %.7f\n" %(x[i], y[i]))
            file.close()

        return newPathFileName
    

    def with_TEGap (self, newGap, xBlend = 0.8):
        """ returns self x,y coordinates with a new te gap.
         The procedere is based on xfoil allowing to define a blending distance from le.

        Arguments: 
            newGap:   in y-coordinates - typically 0.01 or so 
            xblend:   the blending distance from trailing edge 0..1 - Default 0.8
        Returns: 
            x,y:      np coordinate arrays with new Te  (= None if couldn't set)
        """

        # currently le must be at 0,0 - te must be at 1,gap/2 (normalized airfoil) 
        if not self.isNormalized: 
            ErrorMsg ("Airfoil '%s' not normalized. Te gap can't be set." % self.name)
            return self.x, self.y
        
        x = np.copy (self.x) 
        y = np.copy (self.y) 
        xBlend = min( max( xBlend , 0.0 ) , 1.0 )

        gap = y[0] - y[-1]
        dgap = newGap - gap 
        ile = self.iLe

        # go over each point, changing the y-thickness appropriately
        for i in range(len(x)):
            # thickness factor tails off exponentially away from trailing edge
            if (xBlend == 0.0): 
                tfac = 0.0
                if (i == 0 or i == (len(x)-1)):
                    tfac = 1.0
            else:
                arg = min ((1.0 - x[i]) * (1.0/xBlend -1.0), 15.0)
                tfac = np.exp(-arg)

            if i <= ile: 
                y[i] = y[i] + 0.5 * dgap * x[i] * tfac # * gap 
            else:
                y[i] = y[i] - 0.5 * dgap * x[i] * tfac # * gap   
        return x,y 


    def repanel (self): 
        """
        Repanel self with the current values of nPointsNew, le_ and te_bunch.
        The spline of self remains in it's original state """

        # new, equal distribution for upper and lower 
        x, y = self.spline.get_repaneled (self.nPanelsNew, self.le_bunch, self.te_bunch)
        self.set_xy (x, y) 


    def apply_repanel (self):
        """the repaneled x,y will become the new source of truth - the spline will be reinitialized"""

        self._spline = None


    def normalize (self, highPrec = False):
        """
        Shift, rotate, scale airfoil so LE is at 0,0 and TE is symmetric at 1,y
        If 'highPrec' is set, the leading edge of the spline will also be at 0,0.
        """

        # when high precision, normalizing will be done with the spline 
        if highPrec: 
            self.spline._normalize () 
            self.set_xy(self.spline.x, self.spline.y)
            return

        # Translate so that the leading edge is at 0,0 
        xLe, yLe = self.le
        xn = self._x - xLe
        yn = self._y - yLe

        # Rotate the airfoil so chord is on x-axis 
        angle = np.arctan2 ((yn[0] + yn[-1])/ 2.0, (xn[0] + xn[-1])/ 2.0) 
        cosa  = np.cos (-angle) 
        sina  = np.sin (-angle) 

        for i in range (len(xn)):
            xn[i] = xn[i] * cosa - yn[i] * sina
            yn[i] = xn[i] * sina + yn[i] * cosa
         
        # Scale airfoil so that it has a length of 1 
        #  - there are mal formed airfoils with different TE on upper and lower
        #    scale both to 1.0  
        scale_upper = 1.0 / xn[0]
        scale_lower = 1.0 / xn[-1]

        ile = np.argmin (xn)
        for i in range (len(xn)):
            if i <= ile:
               xn[i] = xn[i] * scale_upper
            else: 
               xn[i] = xn[i] * scale_lower

        # due to numerical issues ensure 0 is 0.0 ..
        xn[ile] = 0.0 
        yn[ile] = 0.0 
        xn[0]   = 1.0 
        xn[-1]  = 1.0
        yn[0]   = round(yn[0],10)
        yn[-1]  = round(yn[-1],10)

        self.set_xy (xn, yn)



    def do_strak (self, airfoil1 : 'Airfoil', airfoil2 : 'Airfoil', blendBy):
        """ straks (blends) self out of two airfoils to the left and right
        depending on the blendBy factor"""
    
        # sanity - both airfoils must be noralized 
        if not airfoil1.isLoaded:
            raise ValueError ("Airfoil '" + airfoil1.name + "' isn't loaded. Cannot strak.")
        if not airfoil2.isLoaded:
            raise ValueError ("Airfoil '" + airfoil2.name + "' isn't loaded. Cannot strak.")

        if not airfoil1.isNormalized: airfoil1.normalize()
        if not airfoil2.isNormalized: airfoil2.normalize()

        # the leading airfoil is the one with higher share
        if blendBy <= 0.5:                      # the closer airfoil provides x-coordinates
            x_upper  = airfoil1.upper.x
            x_lower  = airfoil1.lower.x
            y_upper1 = airfoil1.upper.y
            y_lower1 = airfoil1.lower.y
            y_upper2 = airfoil2.spline.get_y_on ("upper", x_upper) 
            y_lower2 = airfoil2.spline.get_y_on ("lower", x_lower) 
        else:
            x_upper  = airfoil2.upper.x
            x_lower  = airfoil2.lower.x
            y_upper1 = airfoil1.spline.get_y_on ("upper", x_upper) 
            y_lower1 = airfoil1.spline.get_y_on ("lower", x_lower) 
            y_upper2 = airfoil2.upper.y
            y_lower2 = airfoil2.lower.y

        # now blend upper and lower of both airfoils 
        y_upper = (1 - blendBy) * y_upper1 + blendBy * y_upper2
        y_lower = (1 - blendBy) * y_lower1 + blendBy * y_lower2
        
        # rebuild x,y coordinates 
        x = np.concatenate ((np.flip(x_upper), x_lower[1:]))
        y = np.concatenate ((np.flip(y_upper), y_lower[1:]))

        self.set_xy (x,y)
        self.sourceName = airfoil1.name + ("_blended_%.2f_" % blendBy) + airfoil2.name
        self.set_isStrakAirfoil (True)



    def plot(self, x=None, y=None):
        """
        Plot the airfoil for testing 
        Alternative coordinates can be supplied 
        """
        import matplotlib.pyplot as plt

        if x is None: x = self.x
        if y is None: y = self.y

        if (x is None or len(x) == 0): 
            ErrorMsg ("No coordinates to plot")
            return 

        fig = plt.figure()
        plt.style.use('seaborn-v0_8-ticks')
        fig.set_figwidth (fig.get_figwidth()  * 2 )     # enlarge window because of 4 plots
        plt.subplots_adjust(left=0.10, bottom=0.10, right=0.95, top=0.90, wspace=None, hspace=None)

        ax = fig.add_subplot(1, 1, 1)
        ax.set_xlim([0.0, 1.0])
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.axis('equal')
        ax.set_title (self.name)
        ax.grid()

        ax.plot(x, y, '-', marker='o', lw=1, fillstyle='none', markersize=4)

        plt.show()    




# ------------ test functions - to activate  -----------------------------------


def test_strak(): 

    import matplotlib.pyplot as plt
    from airfoil_examples import Root_Example, Tip_Example

    # fig, axa = plt.subplots(2, 1, figsize=(16,8))
    # ax1 = axa[0]
    # ax2 = axa[1]

    # ax1.grid(True)
    # ax1.axis("equal")
    # ax2.set_ylim([ -10,  10])

    
    # air1 = Root_Example()
    # air2 = Tip_Example()

    # air1.set_maxThickness (12)
    # air1.set_maxCamber (2.5)
    # air2.set_maxThickness (5)
    
    # airStrak = Airfoil(name="Strak")
    # for i, blendBy in enumerate(np.linspace (0,1, 6)): 
    #     airStrak.do_strak (air1, air2, blendBy)
    #     ax1.plot(airStrak.x, airStrak.y, label="Blend %.2f" % blendBy)
    #     print(i, airStrak.le)
    #     ax2.plot (airStrak.spline.curv_upper.x, airStrak.spline.curv_upper.y, label="Blend %.2f" % blendBy)
    #     ax2.plot (airStrak.spline.curv_lower.x, - airStrak.spline.curv_lower.y, label="Blend %.2f" % blendBy)
    
    # ax1.legend()
    # plt.show()

    # #----

    fig, ax1 = plt.subplots(1, 1, figsize=(16,6))
    ax1.grid(True)
    ax1.axis("equal")

    air1 = Root_Example()
    maxT  = air1.maxThickness
    maxTx = air1.maxThicknessX
    maxCx = air1.maxCamberX
    for i, fac in enumerate (np.linspace (0.5,1.5, 20)):
        # air1.set_maxThickness (maxT * fac)
        # air1.set_maxThicknessX (maxTx * fac) 
        air1.set_maxCamberX (maxCx * fac) 
        ax1.plot(air1.x, air1.y, label="Fac %.2f" % fac)
        print (i)
    ax1.legend()
    plt.show()


if __name__ == "__main__":


    test_strak() 
     
    pass  
