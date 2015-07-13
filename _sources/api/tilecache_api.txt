Tilecache API's
***************

getSimpleTile
-------------

.. http:get:: (string:server_name)/ocptilecache/tilecache/(string:token_name)/(string:channel_name)/(string:slice_type)/(int:time)/(int:zvalue)/(int:ytile)_(int:xtile)_(int:resolution).png
   
   :synopsis: Get a 512x512 tile from the tilecache

   :param server_name: Server Name in OCP. In the general case this is ocp.me.
   :type server_name: string
   :param token_name: Token Name in OCP.
   :type token_name: string
   :param channel_name: Channel Name in OCP. *Optional*. If missing will use default channel for the token.
   :type channel_name: string
   :param slice_type: Type of Slice cutout. Can be xy/yz/xz
   :type slice_type: string
   :param time: Time value. *Optional*. Only possible in timeseries datasets.
   :type time: int
   :param zvalue: Zslice value.
   :type zvalue: int
   :param ytile: Y-Tile value. Each tile is 512x512.
   :type ytile: int
   :param xtile: X-Tile value. Each tile is 512x512.
   :type xtile: int
   :param resolution: Resolution value.
   :type resolution: int

   :statuscode 200: No error
   :statuscode 404: Error in the syntax or file format

getMcfcTile
-----------

.. http:get:: (string:server_name)/ocptilecache/tilecache/mcfc/(string:token_name)/(string:channel_name):(string:color_name)/(string:slice_type)/(int:time)/(int:zvalue)/(int:ytile)_(int:xtile)_(int:resolution).png
   
   :synopsis: Get a 512x512 tile from the tilecache

   :param server_name: Server Name in OCP. In the general case this is ocp.me.
   :type server_name: string
   :param token_name: Token Name in OCP.
   :type token_name: string
   :param channel_name: Channel Name in OCP. *Optional*. If missing will use default channel for the token.
   :type channel_name: string
   :param color_name: Color Name. Can be 'C/M/Y/R/G/B'. *Optional* If Missing will default to "CMYRGB".
   :type color_name: string
   :param slice_type: Type of Slice cutout. Can be xy/yz/xz
   :type slice_type: string
   :param time: Time value. *Optional*. Only possible in timeseries datasets.
   :type time: int
   :param zvalue: Zslice value.
   :type zvalue: int
   :param ytile: Y-Tile value. Each tile is 512x512.
   :type ytile: int
   :param xtile: X-Tile value. Each tile is 512x512.
   :type xtile: int
   :param resolution: Resolution value.
   :type resolution: int

   :statuscode 200: No error
   :statuscode 404: Error in the syntax or file format
