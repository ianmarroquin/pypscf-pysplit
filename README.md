# pypscf-pypsplit

The pysplit package (https://github.com/mscross/pysplit/tree/master/pysplit) is required to use the following python notebook files. To create the trajectory files, use generate_trajectory.ipynb and then cluster_trajectory.ipynb to cluster the resulting trajectories. However, it may be easier to generate the back trajectory files using pyPSCF instead.

# Troubleshooting

With pysplit trajectory generation, check through all the files making sure file names are correct, no missing files or data (check size of file). You may need to download ftp which does not come pre-installed on MacOS (allows you to download the APR files directly from hysplit app).

If files are 0 kb in size, downloading the gdas files directly from the hysplit application seemed to fix the problem.

With clustering, I had to update the directory of the ASCDATA.CFG file and bdyfiles folder. Consult https://www.arl.noaa.gov/documents/reports/hysplit_user_guide.pdf for insight.

Procedure to download brew then ftp:

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

(echo; echo 'eval "$(/opt/homebrew/bin/brew shellenv)"') >> /Users/username/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

brew install inetutils

Type in ftp in the terminal to make sure it is properly installed.
