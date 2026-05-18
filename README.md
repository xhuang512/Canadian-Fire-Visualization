# Understanding Fire Severity in Canada
## Important Note
This actual project was completed as part of UBC DSCI 320 (Visualization for Data Science) by Blake Taylor, Chriscenci Susanto, Daphne Tian, and Xinghao Huang. For portfolio purposes, the original repository has been adapted by removing content authored by other team members; the remaining sections primarily reflect my individual contributions.

Exploring the dashboards here: https://canadian-fire-visualization-mw5cggo2fpjppyn9vt9ufe.streamlit.app/

## Dataset Description
The Canadian National Fire Database (CNFDB) is a comprehensive collection of forest fire locations and perimeters compiled from Canadian fire management agencies across provinces, territories, and Parks Canada. The database is standardized into a common format for Canada-wide analysis, though it contains only fires that agencies have chosen to report and map. The dataset contains information pertaining to forest fires from 1930-2023, for the purposes of our analysis we are focusing on years 2000-2023.

The CNFDB is maintained through a collaborative effort involving all Canadian fire management agencies, with data compilation coordinated at the national level (accessible through https://cwfis.cfs.nrcan.gc.ca). Fire data is collected by individual provincial, territorial, and Parks Canada agencies, including field personnel, fire crews, pilots, and photo interpreters document fire locations and perimeters during and after fire events. This raw data is then processed by digitizers and analysts before being standardized and integrated into the national database. The database serves multiple critical purposes including national-scale mapping, statistical and spatial analysis, and research on natural disturbance patterns in Canadian forests. The compilation was partially funded by several Canadian government programs focused on energy, climate change, and environmental research (ENFOR, Program on Energy Research and Development, Climate Change Action Fund, and Action Plan 2000), reflecting its importance for understanding fire patterns in relation to broader environmental and resource management concerns.

The analysis used a sample dataset of size 20,000 to maintain clarity and computational efficiency.

## Dashboard Preview
Wildfire Event Frequency Over Time by Fire Cause
![Dashboard 1 Demo](images/dashboard%20gifs/Dashboard1XH.gif)

Average Wildfire Size by Severity: Regional and Cause-Based Comparisons
![Dashboard 1 Demo](images/dashboard%20gifs/Dashboard2XH.gif)


## Package requirements
- Pandas
- Altair
- Numpy
- Vega_datasets

## References
- Dataset Documentation: https://cwfis.cfs.nrcan.gc.ca/downloads/nfdb/fire_pnt/current_version/NFDB_point_shapefile_metadata.pdf
- Canadian Wildfire Dataset was collected from: https://cwfis.cfs.nrcan.gc.ca/home

