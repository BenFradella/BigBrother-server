# Big Brother Server Application

Server is set up to send and recieve data as bytes.
In examples bytes are represented similarly to Python: b"some text"

All location data recieved from the server will use N,S,E,W at the end of
latitude/longitude values, rather than using positive/negative numbers.
The server will expect to reveive strings in this format as well. If a string
is received that doesn't match the expected pattern, it will have no effect.

## Sending location data from BigBrother to the server:
*  convert the latitude and longitude from floating point numbers to strings.
*  add N, E, S, or W to the end of each number as appropriate
*  concatenate the strings with commas, and generate the string:
  *  "setLocation (device name) (location)"
*  send two bytes indicating the number of characters to follow, and the string
*  **Example: b"\x00\x22" b"setLocation BB_0 12.4302N,84.2423E"**

## Receiving zone data from server:
*  send a string with two bytes indicating the length of the string to follow
*  the rest of the string is "getZone (device name)"
*  **Example: b"\x00\x0C" b"getZone BB_0"**
*  the server will send a string with three floating point numbers:
*  1st and 2nd are the latitude and longitude of the zone's center point
*  3rd is the zone's radius
*  **Example: b"\x00\x16" b"12.4302N,84.2423E,12.5"**

## Sending zone data to server:
*  send a string with two bytes indicating the length of the string to follow
*  the location data should be formatted similarly to before, with a radius
*  the rest of the string is "setZone (device name) (Latitude,Longitude,radius)"
*  **Example: b"\x00\x23" b"setZone BB_0 12.4302N,84.2423E,12.5"**

## Receiving location data from the server:
*  generate the following string: "getLocation (device name)"
*  format it to bytes as before and send it
*  **Example: b"\x00\x10" b"getLocation BB_0"**
*  the server will respond with the following string: "(Lat,Lon)"
*  **Example: b"\x00\x11" b"12.4302N,84.2423E"**