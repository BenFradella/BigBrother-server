# Big Brother Server Application

Server is set up to send and recieve data as bytes right now.

# Sending location data from BigBrother to the server:
*  convert the latitude and longitude from floating point numbers to strings.
*  add N, E, S, or W to the and of each number as appropriate.
*  concatenate the strings with commas, and generate the string:
*  "setLocation (device name) (location)"
*  send two bytes indicating the number of characters to follow, and the string
*  **Example: b"\x00\x22setLocation BB_0 12.4302N,84.2423E"**

# Receiving zone data from server:
*  send a string with two bytes indicating the length of the string to follow
*  the rest of the string is "getZone (device name)"
*  **Example: b"\x00\x0CgetZone BB_0"**
*  the server will send a string with three floating point numbers:
*  1 and 2 are the latitude and longitude of the zone's center point
*  3 is the zone's radius
*  **Example: b"\x00\x1612.4302N,84.2423E,12.5"**

# Sending zone data to server:
*  send a string with two bytes indicating the length of the string to follow
*  the location data should be formatted similarly to before, with a radius
*  the rest of the string is "setZone (device name) (Latitude,Longitude,radius)"
*  **Example: b"\x00\x23setZone BB_0 12.4302N,84.2423E,12.5"**

# Receiving location data from BigBrother to the server:
*  generate the following string: "getLocation (device name)"
*  format it to bytes as before and send it
*  **Example: b"\x00\x10getLocation BB_0"**
*  the server will respond with the following string: "(Lat,Lon)"
*  **Example: b"\x00\x1112.4302N,84.2423E"**