# jupyroot
Automate common data analysis and visualization tasks using the CERN pyroot library in a jupyter notebook.

Requires prior installation of pyroot (ROOT package) and dask, dask.distributed if parallel
filling of histograms using a dask cluster is desired. Simple example of jupyter notebooks
using the jupyroot classes are included in the repository.

## Application Programmer Interface

  * [jupyroot.treeview](#jupyroot.treeview)
    * [treeview](#jupyroot.treeview.treeview)
      * [\_\_init\_\_](#jupyroot.treeview.treeview.__init__)
      * [declare\_histograms](#jupyroot.treeview.treeview.declare_histograms)
      * [list\_histograms](#jupyroot.treeview.treeview.list_histograms)
      * [enable\_dask\_cluster](#jupyroot.treeview.treeview.enable_dask_cluster)
      * [fill\_histograms](#jupyroot.treeview.treeview.fill_histograms)
      * [setup\_canvas](#jupyroot.treeview.treeview.setup_canvas)
      * [update\_canvas](#jupyroot.treeview.treeview.update_canvas)
      * [draw](#jupyroot.treeview.treeview.draw)
      * [get](#jupyroot.treeview.treeview.get)
      * [put](#jupyroot.treeview.treeview.put)
      * [dask\_dashboard\_link](#jupyroot.treeview.treeview.dask_dashboard_link)
      * [dump\_histodefs](#jupyroot.treeview.treeview.dump_histodefs)
  
  * [jupyroot.hddmview](#jupyroot.hddmview)
    * [hddmview](#jupyroot.hddmview.hddmview)
      * [\_\_init\_\_](#jupyroot.hddmview.hddmview.__init__)
      * [declare\_histograms](#jupyroot.hddmview.hddmview.declare_histograms)
      * [list\_histograms](#jupyroot.hddmview.hddmview.list_histograms)
      * [enable\_dask\_cluster](#jupyroot.hddmview.hddmview.enable_dask_cluster)
      * [fill\_histograms](#jupyroot.hddmview.hddmview.fill_histograms)
      * [setup\_canvas](#jupyroot.hddmview.hddmview.setup_canvas)
      * [update\_canvas](#jupyroot.hddmview.hddmview.update_canvas)
      * [draw](#jupyroot.hddmview.hddmview.draw)
      * [get](#jupyroot.hddmview.hddmview.get)
      * [put](#jupyroot.hddmview.hddmview.put)
      * [dask\_dashboard\_link](#jupyroot.hddmview.hddmview.dask_dashboard_link)
      * [dump\_histodefs](#jupyroot.hddmview.hddmview.dump_histodefs)

<a id="jupyroot.treeview"></a>

# jupyroot.treeview

<a id="jupyroot.treeview.treeview"></a>

## treeview Objects

```python
class treeview()
```

Manages a user-defined collection of ROOT histograms in the form of user
provided functions for declaring each histogram and filling it from the
contents of a ROOT tree chain. Automatic means are provided for running
the fill function over a chain of tree files, and caching the result in
a local ROOT file for quick access the next time it is requested. All
histograms declared to a single treeview object must fill from the same
input tree chain.

<a id="jupyroot.treeview.treeview.__init__"></a>

#### \_\_init\_\_

```python
def __init__(treechain, savetoroot)
```

Constructor required arguments:
 1. treechain = ROOT TChain object that has been configured with the
                list of ROOT files containing the rows of a ROOT tree
                to be analyzed, given in no particular order
 2. saveto = name of a locally writable ROOT file where user histograms
                are cached after filling; if more than one treeview
                object shares the same file then append a directory
                to the filename, as in saveto="myview.root/view_1"

<a id="jupyroot.treeview.treeview.declare_histograms"></a>

#### declare\_histograms

```python
def declare_histograms(setname, initfunc, fillfunc)
```

Declares a list of user-defined histogram to treeview, with arguments:
 1. setname =  user-defined unique name for this set of histograms
 2. initfunc = user-defined function that creates an empty instance of
               these histograms with title and axis labels assigned
 3. fillfunc = user-defined function that accepts a row of a ROOT tree 
               and the list of histograms to be filled as its arguments,
               and fills the histograms from the contents of the tree
Return value is the count of histograms declared.

<a id="jupyroot.treeview.treeview.list_histograms"></a>

#### list\_histograms

```python
def list_histograms(cached=False)
```

Outputs a list of currently declared histograms managed by this object,
returns the count of histograms found.

<a id="jupyroot.treeview.treeview.enable_dask_cluster"></a>

#### enable\_dask\_cluster

```python
def enable_dask_cluster(client)
```

Enable parallel filling of histograms from a chain of input ROOT
tree files, using a dask cluster session provided by the user.

<a id="jupyroot.treeview.treeview.fill_histograms"></a>

#### fill\_histograms

```python
def fill_histograms(chunksize=1)
```

Scan over the full chain of input ROOT files and fill all histograms
that need filling if any, otherwise return immediately. Return value
is the number of histograms that were updated.
 * chunksize - (int) number of input files to process in one dask process,
               only relevant if parallel dask algorithm is enabled

<a id="jupyroot.treeview.treeview.setup_canvas"></a>

#### setup\_canvas

```python
def setup_canvas(prefix="canvas", width=500, height=400)
```

Create a new ROOT canvas for plotting in the output window
of a cell in a jupyter notebook, returns the name.

<a id="jupyroot.treeview.treeview.update_canvas"></a>

#### update\_canvas

```python
def update_canvas(cname=None)
```

Loop through the list of canvases with active plots in them
and issue an update to refresh the display in jupyterhub.

<a id="jupyroot.treeview.treeview.draw"></a>

#### draw

```python
def draw(histos, options="", width=500, height=400, titles=1, stats=1, fits=0)
```

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

<a id="jupyroot.treeview.treeview.get"></a>

#### get

```python
def get(hname)
```

Look for histogram named hname in the cache and return if found,
otherwise look for an empty histogram in the defined histodefs
with this name and return the empty copy, else report error and
return None.

<a id="jupyroot.treeview.treeview.put"></a>

#### put

```python
def put(hist)
```

Save histogram hist in the cache root directory, and
return True for success, False for failure.

<a id="jupyroot.treeview.treeview.dask_dashboard_link"></a>

#### dask\_dashboard\_link

```python
def dask_dashboard_link()
```

The default behavior of the dask client is to provide a local url for
the dask dashboard that is only usable on the local jupyterhub host.
This method returns a link that should work anywhere on the internet,
assuming the jupyterhub host is not blocked by internet firewalls.

<a id="jupyroot.treeview.treeview.dump_histodefs"></a>

#### dump\_histodefs

```python
def dump_histodefs()
```

Scans through the histodefs dictionary  and lists all of the objects
that are registered within the data structure. If any are TH1 objects
then they are checked that they have not been deleted at some point
leaving an invalid reference behind.


## hddmview Objects

```python
class hddmview()
```

Manages a user-defined collection of ROOT histograms in the form of user
provided functions for declaring each histogram and filling it from the
contents of a hddm record. Automatic means are provided for running the
fill function over the list of input hddm files, and caching the result
in a local ROOT file for quick access the next time it is requested. All
histograms declared to a single hddmview object must fill from the same
list of input hddm files.

<a id="jupyroot.hddmview.hddmview.__init__"></a>

#### \_\_init\_\_

```python
def __init__(inputfiles, hddmclass, savetoroot)
```

Constructor required arguments:
 1. inputfiles = list of input hddm files, either as regular unix
                 pathnames or urls of the form root://path/to/file.hddm
                 or http[s]://path/to/file.hddm
 2. hddmclass  = reference to the istream class provided by the hddm
                 module that decodes the  data in the inputfiles, 
                 currently either gluex.hddm_s or gluex.hddm_r
 3. saveto = path to a locally writable ROOT file where user histograms
                 are cached after filling; if more than one hddmview
                 object shares the same file then append a directory
                 to the filename, as in saveto="myview.root/view_1"

<a id="jupyroot.hddmview.hddmview.declare_histograms"></a>

#### declare\_histograms

```python
def declare_histograms(setname, initfunc, fillfunc)
```

Declares a list of user-defined histogram to hddmview, with arguments:
 1. setname =  user-defined unique name for this set of histograms
 2. initfunc = user-defined function that creates an empty instance of
               these histograms with title and axis labels assigned.
 3. fillfunc = user-defined function that accepts a hddm record and the
               list of histograms to be filled as its arguments, and
               fills the histograms from the contents of the hddm record.
Return value is the count of histograms declared.

<a id="jupyroot.hddmview.hddmview.list_histograms"></a>

#### list\_histograms

```python
def list_histograms(cached=False)
```

Outputs a list of currently declared histograms managed by this object,
returns the count of histograms found.

<a id="jupyroot.hddmview.hddmview.enable_dask_cluster"></a>

#### enable\_dask\_cluster

```python
def enable_dask_cluster(client)
```

Enable parallel filling of histograms from different input hddm files,
using a dask cluster session provided by the user, no return value.

<a id="jupyroot.hddmview.hddmview.fill_histograms"></a>

#### fill\_histograms

```python
def fill_histograms(chunksize=1)
```

Scan over the full list of input hddm files and fill all histograms
that need filling if any, otherwise return immediately. Return value
is the number of histograms that were updated.
 * chunksize - (int) number of input files to process in one dask process,
               only relevant if parallel dask algorithm is enabled

<a id="jupyroot.hddmview.hddmview.setup_canvas"></a>

#### setup\_canvas

```python
def setup_canvas(prefix="canvas", width=500, height=400)
```

Create a new ROOT canvas for plotting in the output window
of a cell in a jupyter notebook, returns the name.

<a id="jupyroot.hddmview.hddmview.update_canvas"></a>

#### update\_canvas

```python
def update_canvas(cname=None)
```

Loop through the list of canvases with active plots in them
and issue an update to refresh the display in jupyterhub.

<a id="jupyroot.hddmview.hddmview.draw"></a>

#### draw

```python
def draw(histos, options="", width=500, height=400, titles=1, stats=1, fits=0)
```

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

<a id="jupyroot.hddmview.hddmview.get"></a>

#### get

```python
def get(hname)
```

Look for histogram named hname in the cache and return if found,
otherwise look for an empty histogram in the defined histodefs
with this name and return the empty copy, else report error and
return None.

<a id="jupyroot.hddmview.hddmview.put"></a>

#### put

```python
def put(hist)
```

Save histogram hist in the cache root directory, and
return True for success, False for failure.

<a id="jupyroot.hddmview.hddmview.dask_dashboard_link"></a>

#### dask\_dashboard\_link

```python
def dask_dashboard_link()
```

The default behavior of the dask client is to provide a local url for
the dask dashboard that is only usable on the local jupyterhub host.
This method returns a link that should work anywhere on the internet,
assuming the jupyterhub host is not blocked by internet firewalls.

<a id="jupyroot.hddmview.hddmview.dump_histodefs"></a>

#### dump\_histodefs

```python
def dump_histodefs()
```

Scans through the histodefs dictionary  and lists all of the objects
that are registered within the data structure. If any are TH1 objects
then they are checked that they have not been deleted at some point
leaving an invalid reference behind.
