# -*-coding:Utf-8 -*
import sys
import os
import datetime as dt
from datetime import datetime,timedelta
import numpy as np
import scipy.stats as sst
from scipy.ndimage.filters import gaussian_filter
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import math
import linecache
import pandas as pd


class PSCF:
    """

    Parameters
    ----------
    station : str
        The name of the station.
    specie : str
        The specie to study. Must be specified in the concentration file.
    lat0 : float
        The latitude of the starting point.
    lon0 : float
        The longitude of the starting point.
    folder : str, path
        Path to the backtrajectories files.
    prefix : str
        Prefix of all backtrajectories. Something like 'traj\_OPE\_'
    add_hour : list or array
        List of backtrajecories starting hours around the reference hour.
        Example: add_hour=[-3,0,3] and reference hour of 2017-03-15 09:00,
        the following backtrajectories will be used:

        - 2017-03-15 06:00
        - 2017-03-15 09:00
        - 2017-03-15 12:00

        All theses backtrajecories are associated to the concentration of the
        refrence hour.
    concFile : str, path.
        The path to the concentration file.
    dateMin : str or datetime object
        The minimal date to account.
    dateMax : str or datetime object
        The maximal date to account.
    percentile : int, default 75
        The percentile to use as threshold.
    threshold : float, default None
        The concentration threshold. It overrides the `percentile` value.
    wfunc : boolean, default True
        Either or not use a weighting function.
    wfunc_type : "manual" or "auto", default "auto"
        Type of weighting function. "auto" is continuous.
    mapMinMax : dict
        Dictionary of minimun/maximum of lat/lon for the map.
        Example:
        mapMinMax = {'latmin': 37.5, 'latmax': 60, 'lonmin': -10, 'lonmax': 20}
        This example is the default (France centered).
    cutWithRain : boolean, default True
        Either or not cut the backtrajectory to the last rainning date.
    hourinthepast : integer, default 72
        Number of hour considered for the backtrajectory life.
    resQuality : '110m' or '50m', default '110m'
        The quality of the map.
    smoothplot : boolean, default True
        Use a gaussian filter to smooth the map plot.
    plotBT : boolean, default True
        Either or not plot all the backtraj in a new axe.
    plotPolar : boolean, default True
        Either or not plot the direction the distribution of the PSCF in a
        polar plot.

    Other Parameters
    ----------------
    pd_kwarg : dict, optional
        Dictionary of option pass to pd.read_csv to read the concentration
        file. By default, pd_kwarg={'index_col'=0, 'parse_date'=['date']}.
    """

    def __init__(self, station, specie, lat0, lon0, folder, prefix, add_hour,
                 concFile, dateMin, dateMax, percentile=75, threshold=None,
                 wfunc=True, wfunc_type="auto", resQuality="110m", smoothplot=True,
                 mapMinMax=None, cutWithRain=True, hourinthepast=72,
                 plotBT=True, plotPolar=True, pd_kwarg=None):

        self.station = station
        self.specie = specie
        self.lat0 = float(lat0)
        self.lon0 = float(lon0)
        self.folder = folder
        self.prefix = prefix
        self.add_hour = [float(i) for i in add_hour]
        self.resQuality = resQuality
        self.percentile = percentile
        self.threshold = threshold

        if mapMinMax:
            self.mapMinMax = mapMinMax
        else:
            self.mapMinMax = {'latmin': 37.5, 'latmax': 60,
                              'lonmin': -10, 'lonmax': 20}
        self.dateMin = dateMin
        self.dateMax = dateMax

        # TODO: properly handle pd_kwarg
        self.data = pd.read_table(
           concFile, names=[self.specie,'date'], skiprows=1, sep=","
        )

        self.wfunc = wfunc
        self.wfunc_type = wfunc_type
        self.plotBT = plotBT
        self.plotPolar = plotPolar
        self.smoothplot = smoothplot

        self.cutWithRain = cutWithRain
        self.hourinthepast = hourinthepast

    def toRad(self, x):
        return x*math.pi/180

    def onclick(self, event, plotType):
        """ Find the BT which pass through the clicked cell."""
        ax = plt.gca()

        if event.button == 1 and (event.xdata and event.ydata):
            lon, lat = event.xdata, event.ydata
            lon = np.floor(lon*2)/2
            lat = np.floor(lat*2)/2
            print("Lon/Lat: {:.2f} / {:.2f}".format(lon, lat))
            # find all the BT
            lonNorm = np.floor(self.bt["lon"]*2)/2
            latNorm = np.floor(self.bt["lat"]*2)/2
            df = self.bt[((lonNorm == lon) & (latNorm == lat))]
            if plotType == "PSCF":
                df = df[:][df["conc"] > self.concCrit]
            for i in np.unique(df["dateBT"]):
                tmp = self.bt[:][self.bt["dateBT"] == i]
                ax.plot(tmp["lon"], tmp["lat"], '-', color='0.75')  # , marker='.')
                print("date: {:10} | BT: {:13}h | [x]: {:f}".format(
                    tmp["date"].iloc[0],
                    tmp["dateBT"].iloc[0],
                    tmp["conc"].iloc[0])
                )
            print("")
            sys.stdout.flush()
            event.canvas.draw()
        if event.button == 3:

            ax.lines = []

            if plotType == "allBT":
                var = self.trajdensity_
            elif plotType == "PSCF":
                var = self.PSCF_
            else:
                raise ValueError("`plotType` must be in ['allBT', 'PSCF']")

            if self.smoothplot:
                var = gaussian_filter(var, 1)

            ax.pcolormesh(self.lon_map, self.lat_map, var.T, cmap='hot_r')
            ax.plot(self.lon0, self.lat0, 'o', color='0.75')
            event.canvas.draw()


    def extractBackTraj(self):

        df = pd.DataFrame()

        for filename, date in zip(os.listdir(self.folder), self.data["date"]):

            file_path = os.path.join(self.folder, filename)
            
            for hour in self.add_hour:
                if filename[0] ==".":
                    continue

                else:
                    # add the lon/lat of the BT
                    nb_line_to_skip = linecache.getline(file_path, 1).split()
                    nb_line_to_skip = int(nb_line_to_skip[0])
                    meteo_idx = linecache.getline(file_path, nb_line_to_skip+4).split()
                    idx_names = [
                        "a", "b", "year", "month", "day", "hour", "c", "d",
                        "run", "lat", "lon", "alt"
                    ]
                    idx_names = np.hstack((idx_names, meteo_idx[1:]))

                    traj = pd.read_table(
                        file_path,
                        header=None,
                        sep="\s+",
                        names=idx_names,
                        skiprows=nb_line_to_skip+4,
                        nrows=self.hourinthepast
                    )
                    lat = traj["lat"]
                    lon = traj["lon"]
                    rain = traj["RAINFALL"]

                    # if it was raining at least one time, we cut it
                    if self.cutWithRain and any(rain > 0):
                        idx_rain = np.where(rain != 0)[0][0]
                        lat = lat[:idx_rain]
                        lon = lon[:idx_rain]

                    dftmp = pd.DataFrame(data={
                        "date": date,
                        "dateBT": datetime.strptime(date,"%Y-%m-%d")+dt.timedelta(hours=hour),
                        "conc": self.data[self.specie],
                        "lon": lon,
                        "lat": lat
                    })
#fix dateBT 
                df = pd.concat([df, dftmp])

        return df

    def run(self):
        """Run the PSCF model and add 4 attributes to the PSCF object:

        Returns
        -------
        ngrid_ : ndarray
            The number of end-point of back-trajectories in each grid cell
        mgrid_ : ndarray
            The number of en-point of back-trajectories in each grid cell
            accociated with concentration > self.concCrit
        PSCF_ : ndarray
            mgrid/ngrid, the PSCF data.
        trajdensity_ : ndarray
            log_10(ngrid)
        """

        specie = self.specie
        percentile = self.percentile
        threshold = self.threshold
        data = self.data
        mapMinMax = self.mapMinMax

        # extract relevant info
        # date format for the file "YYYY-MM-DD HH:MM"
        data = data[(data.index > min(data.index)) & (data.index < max(data.index))]

        self.date = data.index

        self.conc = data[specie]

        # ===== critical concentration
        if percentile:
            concCrit = sst.scoreatpercentile(self.conc, percentile)
        elif threshold:
            concCrit = threshold
        else:
            raise ValueError("'percentile' or 'threshold' shoud be specified.'")
        # if len(concCrit)==1:
        #     concCrit = concCrit[0]
        self.concCrit = concCrit

        # ===== Extract all back-traj needed        ===========================
        self.bt = self.extractBackTraj()

        # ===== convert lon/lat to 0, 0.5, 1, etc
        # +0.1 in order to have the max in the array
        self.lon = np.arange(mapMinMax["lonmin"], mapMinMax["lonmax"]+0.01, 0.5)
        self.lat = np.arange(mapMinMax["latmin"], mapMinMax["latmax"]+0.01, 0.5)
        self.lon_map, self.lat_map = np.meshgrid(self.lon, self.lat)

        ngrid, xedges, yedges = np.histogram2d(
            self.bt["lon"],
            self.bt["lat"],
            bins=[
                np.hstack((self.lon,
                           self.lon[-1]+0.5)),
                np.hstack((self.lat,
                           self.lat[-1]+0.5))
            ]
        )
        maskgtconcCrit = self.bt["conc"] >= concCrit
        mgrid, xedges, yedges = np.histogram2d(
            self.bt.loc[maskgtconcCrit, "lon"],
            self.bt.loc[maskgtconcCrit, "lat"],
            bins=[
                np.hstack((self.lon,
                           self.lon[-1]+0.5)),
                np.hstack((self.lat,
                           self.lat[-1]+0.5))
            ]
        )

        not0 = np.where(ngrid != 0)

        PSCF = np.zeros(np.shape(ngrid))
        PSCF[not0] = mgrid[not0]/ngrid[not0]

        trajdensity = np.zeros(np.shape(ngrid))
        trajdensity[not0] = np.log10(ngrid[not0])

        # ===== Weighting function
        if self.wfunc:
            wF = np.zeros(np.shape(ngrid))
            # TODO: "manual" is not yet implemented in the API
            if self.wfunc_type == "manual":
                self.wfunc_type = "auto"

            if self.wfunc_type == "manual":
                wFlim = np.array([float(param["wFlim"][0]), float(param["wFlim"][1]), float(param["wFlim"][2])]) * trajdensity.max()
                wFval = np.array([float(param["wFval"][0]), float(param["wFval"][1]), float(param["wFval"][2]), float(param["wFval"][3])])

                wF[np.where(trajdensity < wFlim[0])] = wFval[0]
                wF[np.where((trajdensity >= wFlim[0]) & (trajdensity < wFlim[1]))] = wFval[1]
                wF[np.where((trajdensity >= wFlim[1]) & (trajdensity < wFlim[2]))] = wFval[2]
                wF[np.where(trajdensity >= wFlim[2])] = wFval[3]
            elif self.wfunc_type == "auto":
                # m0 = np.where(mgrid !=0)
                # wF[m0] = np.log(mgrid[m0])/np.log(ngrid.max())
                wF[not0] = np.log(ngrid[not0])/np.log(mgrid.max())

            PSCF = PSCF * wF

        self.ngrid_ = ngrid
        self.mgrid_ = mgrid
        self.PSCF_ = PSCF
        self.trajdensity_ = trajdensity


    def _prepare_figure(self):
        """Set the base of a map figure

        :returns: (fig, ax)

        """
        fig = plt.figure()  # keep handle for the onclick function
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        ax.set_extent(
            [
                self.mapMinMax["lonmin"],
                self.mapMinMax["lonmax"],
                self.mapMinMax["latmin"],
                self.mapMinMax["latmax"],
            ],
            ccrs.PlateCarree()
        )
        return (fig, ax)


    def _plot_pcolormesh(self, data, fig=None, ax=None):
        """Plot the 2D data `data` on a figure using pcolormesh
        """

        if (fig is None) and (ax is None):
            fig, ax = self._prepare_figure()

        if self.smoothplot:
            d = gaussian_filter(data, 1)
        else:
            d = data

        ax.coastlines(resolution=self.resQuality)
        ax.add_feature(cfeature.BORDERS.with_scale(self.resQuality),
                       edgecolor='grey')

        pmesh = ax.pcolormesh(self.lon_map, self.lat_map, d, cmap='BuPu')

        ax.plot(self.lon0, self.lat0, 'r', color='0.75')


    def plot_backtraj(self):
        """Plot a map of all trajectories.
        """
        print(self)
        fig, ax = self._prepare_figure()

        self._plot_pcolormesh(self.trajdensity_.T, fig=fig, ax=ax)

        plotTitle = "{station}\nBacktrajectories probability (log(n))".format(
            station=self.station
        )
        ax.set_title(plotTitle)

        cid = fig.canvas.mpl_connect('button_press_event',
                                       lambda event: self.onclick(event, "allBT"))
        fig.canvas.set_window_title(self.station+"_allBT")


    def plot_PSCF(self):
        """Plot the PSCF map.
        """
        fig, ax = self._prepare_figure()

        self._plot_pcolormesh(self.PSCF_.T, fig=fig, ax=ax)

        plotTitle = "{station}, {specie} > {concCrit:.2f}\nFrom {dmin} to {dmax}".format(
            station=self.station, specie=self.specie,
            concCrit=self.concCrit,
            dmin=min(self.data["date"]),
            dmax=max(self.data["date"])
        )
        ax.set_title(plotTitle)

        cid = fig.canvas.mpl_connect('button_press_event',
                                     lambda event: self.onclick(event, "PSCF"))
        fig.canvas.set_window_title(self.station+self.specie)


    def plot_PSCF_polar(self):
        """ Plot a polar plot of the PSCF
        """
        # change the coordinate system to polar from the station point
        deltalon = self.lon0 - self.lon
        mesh_deltalon, mesh_lat = np.meshgrid(deltalon, self.lat)
        mesh_lon, _ = np.meshgrid(self.lon, self.lat)
        mesh_deltalon = self.toRad(mesh_deltalon)
        mesh_lon = self.toRad(mesh_lon)
        mesh_lat = self.toRad(mesh_lat)

        a = np.sin(mesh_deltalon) * np.cos(mesh_lat)
        b = np.cos(self.lat0*math.pi/180)*np.sin(mesh_lat) \
            - np.sin(self.lat0*math.pi/180)*np.cos(mesh_lat)*np.cos(mesh_deltalon)
        bearing = np.arctan2(a, b)
        bearing += math.pi/2  # change the origin: from N to E
        bearing[np.where(bearing < 0)] += 2*math.pi  # set angle between 0 and 2pi
        bearing = bearing.T

        # select and count the BT in a given Phi range
        mPhi = list()
        theta = self.toRad(np.arange(0, 361, 22.5))
        mPhi.append(np.sum(self.mgrid_[np.where(bearing <= theta[1])]))
        for i in range(1, len(theta)-1):
            mPhi.append(np.sum(self.mgrid_[np.where((theta[i] < bearing) &
                                                    (bearing <= theta[i+1]))]))
        # convert it in percent
        values = mPhi/np.sum(self.mgrid_)*100

        # ===== Plot part
        figPolar = plt.figure()
        xticklabel = ['E', 'NE', 'N', 'NW', 'W', 'SW', 'S', 'SE']

        axPolar = plt.subplot(111, projection='polar')
        bars = axPolar.bar(theta[:-1], values, width=math.pi/8, align="edge")
        axPolar.xaxis.set_ticklabels(xticklabel)
        axPolar.yaxis.set_ticks(range(0, int(max(values)), 5))

        plotTitle = "{station}, {specie} > {concCrit}\nFrom {dmin} to {dmax}".format(
            station=self.station, specie=self.specie, concCrit=self.concCrit,
            dmin=min(self.data["date"]),
            dmax=max(self.data["date"])
        )
        plt.subplots_adjust(top=0.85, bottom=0.05, left=0.07, right=0.93)
        figPolar.canvas.set_window_title(self.station+self.specie+"_windrose")
        
