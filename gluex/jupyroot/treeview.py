#!/usr/bin/env python3
#
# treeview - python class that acts as a container of ROOT (see https://root.cern.ch)
#            objects for statistical visualization of data contained in ROOT trees
#            (see https://root.cern.ch/root/htmldoc/guides/users-guide/Trees.html)
#            Users define the ROOT histograms that visualize the data in interesting
#            ways, together with methods for filling those histograms from the column
#            data contained in a ROOT tree chain, and identify those histograms with
#            a unique user-assigned string name.  The treeview object then fills the
#            histograms by scanning through the ROOT tree chain provided by the user,
#            and caches the result for future reference.  Methods for displaying the
#            histograms in a jupyter notebook are also provided. 
#
# author: richard.t.jones at uconn.edu
# version: september 12, 2024
# notes: See "pydoc jupyroot.treeview" for details of the API.

import ROOT
import dask
import dask.distributed
from pyxrootd import client as xclient
import IPython.display

import os
import sys
import socket
import re

class treeview:
   """
   Manages a user-defined collection of ROOT histograms in the form of user
   provided functions for declaring each histogram and filling it from the
   contents of a ROOT tree chain. Automatic means are provided for running
   the fill function over a chain of tree files, and caching the result in
   a local ROOT file for quick access the next time it is requested. All
   histograms declared to a single treeview object must fill from the same
   input tree chain.
   """

   def __init__(self, treechain, savetoroot):
      """
      Constructor required arguments:
       1. treechain = ROOT TChain object that has been configured with the
                      list of ROOT files containing the rows of a ROOT tree
                      to be analyzed, given in no particular order
       2. saveto = name of a locally writable ROOT file where user histograms
                      are cached after filling; if more than one treeview
                      object shares the same file then append a directory
                      to the filename, as in saveto="myview.root/view_1"
      """
      self.inputchain = treechain
      self.memorydir = ROOT.TDirectory(savetoroot.replace('/', '.') + "_resident",
                                       "histograms cached in memory")
      rootpath = savetoroot.split('/')
      isfile = 1
      while os.path.isdir('/'.join(rootpath[:isfile])):
         isfile += 1
      self.savetorootfile = '/'.join(rootpath[:isfile])
      self.savetorootdir = '/'.join(rootpath[isfile:])
      if os.path.isfile(self.savetorootfile):
         f = ROOT.TFile(self.savetorootfile, "update")
         if self.savetorootdir:
            found = sum([1 for key in f.GetListOfKeys() 
                         if self.savetorootdir == key.GetName()])
            if not found:
               f.mkdir(self.savetorootdir)
      else:
         f = ROOT.TFile(self.savetorootfile, "recreate")
         f.mkdir(self.savetorootdir)
      f.Close()
      self.histodefs = {}
      self.dask_client = None
      self.canvases = {}
      self.current_canvas = None
      self.drawn_histos = {}

   def declare_histograms(self, setname, initfunc, fillfunc):
      """
      Declares a list of user-defined histogram to treeview, with arguments:
       1. setname =  user-defined unique name for this set of histograms
       2. initfunc = user-defined function that creates an empty instance of
                     these histograms with title and axis labels assigned
       3. fillfunc = user-defined function that accepts a row of a ROOT tree 
                     and the list of histograms to be filled as its arguments,
                     and fills the histograms from the contents of the tree
      Return value is the count of histograms declared.
      """
      savedir = ROOT.gDirectory
      ROOT.gDirectory = ROOT.TDirectory("scratch", "scratch workspace")
      nhistos = 0
      for hname,histo in initfunc().items():
         if hname != histo.GetName():
            print("treeview.declare_histograms error -",
                  "histogram", hname, "does not match the ROOT object name",
                  histo.GetName() + ", please fix this and try again.")
            ROOT.gDirectory = savedir
            return nhistos
         nhistos += 1
      ROOT.gDirectory = savedir
      self.histodefs[setname] = {'init': initfunc, 'fill': fillfunc, 'filled': {}}
      return nhistos

   def list_histograms(self, cached=False):
      """
      Outputs a list of currently declared histograms managed by this object,
      returns the count of histograms found.
      """
      nhistos = 0
      if not cached:
         savedir = ROOT.gDirectory
         tmpdir = ROOT.TDirectory("tmp", "temporary for list_histograms")
         for hset,histodef in self.histodefs.items():
            ROOT.gDirectory = tmpdir
            for hname,histo in histodef['init']().items():
               print("{0:15s}".format(histo.GetName()), end="")
               print(" {0:60s}".format(histo.GetTitle()), end="")
               try:
                  print(" {0}".format(histodef['filled'][hname].GetEntries()))
                  nhistos += 1
               except:
                  with ROOT.TFile(self.savetorootfile) as fsaved:
                     if self.savetorootdir:
                        ROOT.gDirectory.cd(self.savetorootdir)
                     try:
                        histodef['filled'][hname] = ROOT.gDirectory.Get(hname)
                        histodef['filled'][hname].SetDirectory(self.memorydir)
                        print(" {0}".format(histodef['filled'][hname].GetEntries()))
                        nhistos += 1
                     except:
                        print(" {0}".format(" unfilled"))
                        del histodef['filled'][hname]
         ROOT.gDirectory = savedir
      else:
         with ROOT.TFile(self.savetorootfile) as fsaved:
            if self.savetorootdir:
               ROOT.gDirectory.cd(self.savetorootdir)
            for key in ROOT.gDirectory.GetListOfKeys():
                histo = key.ReadObj()
                if isinstance(histo, ROOT.TH1):
                   print("{0:15s}".format(histo.GetName() + f";{key.GetCycle()}"), end="")
                   print(" {0:45s}".format(histo.GetTitle()), end="")
                   print(" {0:10.0f}".format(histo.GetEntries()), end="")
                   print("   {0}".format(key.GetDatime().AsString()))
                   nhistos += 1
      return nhistos

   def enable_dask_cluster(self, client):
      """
      Enable parallel filling of histograms from a chain of input ROOT
      tree files, using a dask cluster session provided by the user.
      """
      self.dask_client = client

   def fill_histograms(self, chunksize=1):
      """
      Scan over the full chain of input ROOT files and fill all histograms
      that need filling if any, otherwise return immediately. Return value
      is the number of histograms that were updated.
       * chunksize - (int) number of input files to process in one dask process,
                     only relevant if parallel dask algorithm is enabled
      """
      workdir = ROOT.TDirectory(self.memorydir.GetName() + "_workspace",
                                self.memorydir.GetTitle() + "_workspace")
      savedir = ROOT.gDirectory
      workdir.cd()
      nfiles = self.inputchain.GetNtrees()
      def fill_histograms_hinit():
         return {'fill_histograms_stats':
                 ROOT.TH1D("fill_histograms_stats", "file processing statistics", nfiles, 0, nfiles)}
      def fill_histograms_hfill(ifile, histos):
         histos['fill_histograms_stats'].Fill(ifile)
      self.declare_histograms("fill_histograms statistics", fill_histograms_hinit, fill_histograms_hfill)
      ntofill = 0
      for hset,histodef in self.histodefs.items():
         histos = histodef['init']()
         with ROOT.TFile.Open(self.savetorootfile) as fsaved:
            if self.savetorootdir:
               ROOT.gDirectory.cd(self.savetorootdir)
            try:
               histodef['filled'] = {h: ROOT.gDirectory.Get(h) for h in histos}
               [h.GetTitle() for h in histodef['filled'].values()]
               histodef['filled'] = {}
            except:
               histodef['filled'] = {}
               histodef['filling'] = histos
               ntofill += len(histos)
      if ntofill > 0 and self.dask_client is None:
         print("found", ntofill, "histograms that need filling,",
               "doing that now in sequential mode...")
         for row in self.inputchain:
            for hkey,histodef in self.histodefs.items():
               if 'filling' in histodef:
                  if hkey == "fill_histograms statistics":
                     ifile = self.inputchain.GetTreeNumber()
                     histodef['fill'](ifile, histodef['filling'])
                  else:
                     histodef['fill'](row, histodef['filling'])
      elif ntofill > 0:
         print("found", ntofill, "histograms that need filling,",
               "follow progress on dask monitor dashboard at",
               self.dask_dashboard_link())
         treename = self.inputchain.GetName()
         inputfiles = [link.GetTitle() for link in self.inputchain.GetListOfFiles()]
         results = [dask.delayed(dask_treeplayer)(j, inputfiles[j:j+chunksize], treename, self.histodefs)
                    for j in range(0, len(inputfiles), chunksize)]
         round2 = [dask.delayed(dask_collector)(results[i*100:(i+1)*100])
                   for i in range((len(results) + 99) // 100)]
         lastround = dask.delayed(dask_collector)(round2)
         for hset,histodef in lastround.compute().items():
            if 'filling' in histodef:
               self.histodefs[hset]['filling'] = histodef['filling']
      with ROOT.TFile.Open(self.savetorootfile, "update") as fsaved:
         if self.savetorootdir:
            ROOT.gDirectory.cd(self.savetorootdir)
         for histodef in self.histodefs.values():
            if 'filling' in histodef:
               for h in histodef['filling'].values():
                  h.Write()
                  h.SetDirectory(self.memorydir)
                  #print("filled histogram", h.GetName(), "with", h.GetEntries(), "entries")
               histodef['filled'] = histodef['filling']
               del histodef['filling']
      hprocstats = self.get('fill_histograms_stats')
      nfiles = sum([1 for i in range(nfiles) if hprocstats.GetBinContent(i+1) > 0])
      nrecords = hprocstats.Integral()
      print(f"fill_histograms read a total of {nfiles} tree files, {nrecords} records")
      #workdir.ls()
      savedir.cd()
      return ntofill

   def setup_canvas(self, prefix="canvas", width=500, height=400):
      """
      Create a new ROOT canvas for plotting in the output window
      of a cell in a jupyter notebook, returns the name.
      """
      cname = f"canvas{id(self)}"
      self.canvases[cname] = ROOT.TCanvas(cname, "", width, height)
      self.current_canvas = self.canvases[cname]
      return cname

   def update_canvas(self, cname=None):
      """
      Loop through the list of canvases with active plots in them
      and issue an update to refresh the display in jupyterhub.
      """
      if cname:
         self.canvases[cname].cd(0)
         self.canvases[cname].Update()
         IPython.display.display(self.canvases[cname])
      else:
         for canv in self.canvases.values():
            canv.cd(0)
            canv.Update()
            IPython.display.display(canv)

   def draw(self, histos, options="", width=500, height=400,
            titles=1, stats=1, fits=0):
      """
      Emulates the TH1.Draw() method for an array of histograms.
       1) histos - name of histogram to draw, or multidimensional array
                   of the names of histograms to be drawn;
          [..] if histos is a one-dimensional list then the histograms
                   identified in the list are drawn in equal-size divisions
                   across a single row, with each plot occupying width x
                   height in the drawing area of the canvas;
          [[..]..] if histos is a two-dimensional list then the histograms
                   are drawn on a rectangular grid of equal-size boxes,
                   each of dimension width x height;
          [[[..]..]..] if histos is a three-dimensional list then it is
                   treated like a two-dimensional array, with the histograms
                   listed in the third dimension all drawn on the same plot;
       2) options - a string or array of strings with the same shape as
                   histos, that is passed to TH1.Draw in the option argument;
       3) width - optional argument giving the pixel width of each plot;
       4) height - optional argument giving the pixel height of each plot;
       5) titles - 1/0 for whether to display histogram titles or not;
       6) stats - 1/0 for whether to display statistics boxes or not;
       7) fits - 1/0 for whether to display fit parameter boxes or not;
      Return value is the total number of histograms plotted.
      """
      ROOT.gStyle.SetOptTitle(titles)
      ROOT.gStyle.SetOptStat(stats)
      ROOT.gStyle.SetOptFit(fits)
      badoption = 0
      nhistos = 0
      if isinstance(histos, list):
         ny = len(histos)
         if isinstance(options, list):
            try:
               u = options[ny-1]
            except:
               badoption = 1
         if isinstance(histos[0], list):
            wx = [len(histos[i]) for i in range(ny)]
            nx = max(wx)
            if isinstance(options, list):
               try:
                  u = options[wx.index(nx)][nx-1]
               except:
                  badoption = 2
         else:
            nx = ny
            ny = 0
            if isinstance(options, list):
               if not isinstance(options[0], str):
                  badoption = 3
      else:
         ny = 0
         nx = 0
         try:
            if isinstance(options, list):
               u = options[0]
               badoption = 4
         except:
            pass
      if badoption:
         raise ValueError("arguments histos and options must have " +
                          "the same shape if either one of them " +
                          f"is an array or a list ({badoption})")
      if nx == 0 and ny == 0:
         cname = self.setup_canvas(width=width, height=height)
         histo = self.get(histos)
         histo.Draw(options)
         nhistos += 1
         self.drawn_histos[histo.GetName()] = histo
      elif ny == 0:
         cname = self.setup_canvas(width=width*nx, height=height)
         self.current_canvas.Divide(nx, 1)
         for ix in range(nx):
            self.current_canvas.cd(ix + 1)
            histo = self.get(histos[ix])
            if isinstance(options, list):
               histo.Draw(options[ix])
            else:
               histo.Draw(options)
            nhistos += 1
            self.drawn_histos[histo.GetName()] = histo
      else:
         cname = self.setup_canvas(width=width*nx, height=height*ny)
         self.current_canvas.Divide(nx, ny)
         for iy in range(ny):
            for ix in range(nx):
                try:
                  self.current_canvas.cd(iy * nx + ix + 1)
                  if isinstance(histos[iy][ix], list):
                     histo = self.get(histos[iy][ix][0])
                     if isinstance(options, list):
                        histo.Draw(options[iy][ix][0])
                        nhistos += 1
                        self.drawn_histos[histo.GetName()] = histo
                        for i in range(1,len(histos[iy][ix])):
                           histo = self.get(histos[iy][ix][i])
                           histo.Draw(options[iy][ix][0] + " same")
                           nhistos += 1
                           self.drawn_histos[histo.GetName()] = histo
                     else:
                        histo.Draw(options)
                        nhistos += 1
                        self.drawn_histos[histo.GetName()] = histo
                        for i in range(1,len(histos[iy][ix])):
                           histo = self.get(histos[iy][ix][i])
                           histo.Draw(options + " same")
                           nhistos += 1
                           self.drawn_histos[histo.GetName()] = histo
                  else:
                     histo = self.get(histos[iy][ix])
                     if isinstance(options, list):
                        histo.Draw(options[iy][ix])
                        nhistos += 1
                     else:
                        histo.Draw(options)
                        nhistos += 1
                     self.drawn_histos[histo.GetName()] = histo
                except:
                  pass
      self.current_canvas.cd(0)
      self.current_canvas.Draw()
      return nhistos

   def get(self, hname):
      """
      Look for histogram named hname in the cache and return if found,
      otherwise look for an empty histogram in the defined histodefs
      with this name and return the empty copy, else report error and
      return None.
      """
      with ROOT.TFile(self.savetorootfile) as fsaved:
         if self.savetorootdir:
            ROOT.gDirectory.cd(self.savetorootdir)
         try:
            h = ROOT.gDirectory.Get(hname)
            h.SetDirectory(self.memorydir)
            return h
         except:
            pass
      h = None
      for hset,histoset in self.histodefs.items():
         for histo in histoset['init']().values():
            if hname == histo.GetName():
               h = histo
            else:
               histo.Delete()
      h.SetDirectory(self.memorydir)
      return h

   def put(self, hist):
      """
      Save histogram hist in the cache root directory, and
      return True for success, False for failure.
      """
      with ROOT.TFile(self.savetorootfile, "update") as fsaved:
         if self.savetorootdir:
            ROOT.gDirectory.cd(self.savetorootdir)
         try:
            hist.Write()
         except:
            return False
      return True

   def dask_dashboard_link(self):
      """
      The default behavior of the dask client is to provide a local url for
      the dask dashboard that is only usable on the local jupyterhub host.
      This method returns a link that should work anywhere on the internet,
      assuming the jupyterhub host is not blocked by internet firewalls.
      """
      if self.dask_client:
         return re.sub("127.0.0.1", socket.getfqdn(), self.dask_client.dashboard_link)
      else:
         return None

   def dump_histodefs(self):
      """
      Scans through the histodefs dictionary  and lists all of the objects
      that are registered within the data structure. If any are TH1 objects
      then they are checked that they have not been deleted at some point
      leaving an invalid reference behind. 
      """
      print("declared histodefs:")
      for hset,histodef in self.histodefs.items():
         print(f"  {hset}:")
         for keyword in histodef:
            if keyword == 'filled' or keyword == 'filling':
               print(f"      '{keyword}':")
               for hname,histo in histodef[keyword].items():
                  print(f"        {hname}:", end=' ')
                  try:
                     print(histo.GetName(), histo.GetTitle(), end=' ')
                     print(histo.GetEntries())
                  except:
                     print("*** invalid reference to TH1 object ***")
            else:
               print(f"      '{keyword}':", histodef[keyword])

def dask_treeplayer(j, infiles, treename, histodefs):
   """
   Static member function of treeview, called with dask_delayed
   to fill histograms from ROOT tree input files in parallel on
   a dask cluster.
    1. j - (int) starting index of file for this process
    2. infiles - list of path or url to the input ROOT tree file
    3. histodefs - copy of treeview.histodefs structure with lists of TH1
                  histograms being filled under the key 'filling'.
   Return value is the updated histodefs from argument 4.
   """
   for infile in infiles:
      try:
         froot = ROOT.TFile.Open(infile)
         tree = ROOT.gDirectory.Get(treename)
         for row in tree:
            for hset,histodef in histodefs.items():
               if hset == "fill_histograms statistics":
                  histodef['fill'](j, histodef['filling'])
               elif 'filling' in histodef:
                  try:
                     histodef['fill'](row, histodef['filling'])
                  except:
                     pass
      except:
         pass
      j += 1
   return histodefs

def dask_collector(results):
   """
   Static member function of treeview, called with dask_delayed
   to sum a list of histogram sets formed from the return values
   of dask_treeplayer instances run in parallel on a dask cluster.
   Return value is the sum of the individual results.
   """
   resultsum = results[0]
   for hset in resultsum:
      if 'filling' in resultsum[hset]:
         for h in resultsum[hset]['filling']:
            for result in results[1:]:
               resultsum[hset]['filling'][h].Add(result[hset]['filling'][h])
   return resultsum
