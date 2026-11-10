# F1trackdata
A Python project that visualises a driver's fastest qualifying lap . It uses the OpenF1 API to fetch lap data, asks the user to choose a race and driver , and plots the circuit from the car's recorded x-y coordinates . The track is colour coded by speed , with markers for braking zones , the top speed point, and high speed sections.
Speed and position data are recorded at slightly different moments, so the two datasets are aligned by time using interpolation.
Built with: Python, requests, pandas, NumPy, Matplotlib
