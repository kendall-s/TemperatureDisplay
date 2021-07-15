# Temperature Display / Logger

#### Simple PyQt app for logging and display temperature probe data. Displays chart of last hour worth of data along with current temperature readout and standard deviation for last hour 📉

## Usage

Download and run the .exe, select the correct serial port that the temperature probe is running on, browse to the folder where you want data recorded, click "Start Acquire". 



## Background

A serial output temperature logger was manufactured by T.Goodwin at CSIRO, this compact unit runs on 12V DC and the temperature probe is NATA certified to 4 significant digits for temperature.

The device outputs a data string every second that contains temperature as well as other data pertaining the the temperature control functionality built into the board.

Example output string:


```
T=22.12601 Err.=24.12601 S.P.=-2.00000 f.ave=   0 control=0 raw=1.01629340\n
```

Using pyserial readline api, this string can be consumed, interpreted and the data saved to disk.



 

