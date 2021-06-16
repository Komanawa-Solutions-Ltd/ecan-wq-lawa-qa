ECan LAWA QA script
===================================================================

Intro
-----
This repo contains a script (qa_checks.py) to run several quality assessment checks on surface water quality data. The python environment should be set up from the accompanying env.yml or requirements.txt. The outputs are saved in the results folder.

Installation
------------
Download and install GitHub Desktop
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Go to `<https://desktop.github.com/>`_ and download and install GitHub Desktop. No admin rights required. This program helps you manage all of your Git repositories. A user guide can be found here: `<https://help.github.com/en/desktop>`_.

Clone this repository
~~~~~~~~~~~~~~~~~~~~~
Use GitHub Desktop to clone this repository or download the zip via the green "code" dropdown menu. Save the contents to an appropriate place on your PC.

Download and install Miniconda
------------------------------
Download and install the recommended Python installation called `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_. No admin rights required. A user guide can be found here: `<https://docs.conda.io/projects/conda/en/latest/user-guide/index.html>`_. A nice "Cheat sheet"  can be downloaded here: `<https://docs.conda.io/projects/conda/en/latest/user-guide/cheatsheet.html>`_.

Create a Python environment to run the example code
---------------------------------------------------
The env.yml file defines the required packages dependencies for the qa_checks.py.

To install via conda, type the following into the anaconda prompt when in the root directory::

  conda env create -f env.yml

Running the script
------------------
To run the qa_checks.py script. Only the anaconda prompt and type in the following to switch to your new python environment::

  conda activate lawa-qa

Then navigate to the folder containing the script or run the script with the full path to the script::

  python C:\path\to\script\qa_checks.py

As mentioned in the Intro, the output csv files will be saved to the results folder. The entire process might take several minutes to extract all of the data.

QA checks types
------------------
Four different checks are made on the sample results. These include the number of `standard deviations <https://en.wikipedia.org/wiki/Standard_deviation>`_ from the mean, the number of `interquartile ranges <https://en.wikipedia.org/wiki/Interquartile_range>`_ (IQR) from the 3rd quartile, values above or below the detection limits, and user defined minimum and maximum values for the measurement types.


Changing the parameters.yml
----------------------------
There are several parameters that can be changed to adjust how the script runs. The parameters.yml file is in the same folder as the qa_checks.py file. The api_endpoint is the base url to the Hilltop server (probably shouldn't be changed). The hts is the "hts" file (it's also the dsn file name, but you still need the hts extension) to read from. The std_factor is the number of standard deviations from the mean to use as an outlier detector. Similarly, the iqr_factor is the number of IQRs from the 3rd quartile to use as an outlier detector. The mtypes field contains the measurements and the global minimum and maximum values to be checked. More measurements can be added (or removed) from the mtypes field as required.
