
# key to make an integer index 

def tileKey ( dsid, r, x, y, z ):
  """Make a 64 bit key from a tile"""

  # 8 bits for r and 8 bits for project id
  highkey = (r & 0XFFFF) + (dsid << 16)
  lowkey = (x & 0XFFFFF) + ((y & 0xFFFFF) << 20) + ((z & 0xFFFFF) << 40) 
  return (highkey,lowkey)

