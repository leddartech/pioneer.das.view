"""dasview v0.1
Usage:
  dasview <folder>
  dasview <folder> [options] 

Options:
-h --help                show this help message and exit
  --version              show version and exit
  --include=<inc>        exclusively included sensors in platform [default: ]
  --ignore=<ign>         ignored sensors in platform [default: ]
  --add_sync=<source>    given source will also be synchronized [default: ]
  --video_recording_enable        desactivate the qt multi-threading, and then enable frame grabing for video recording
  --video_fps=<int>      force video fps to a specific value, else compute from datasource timestamps
"""

from pioneer.das.api import platform
from pioneer.das.view.viewer import Viewer

from docopt import docopt

import os

DEFAULT_IGNORE_LABELS = ['radarTI_bfc']

def main():
    import os
    version = '0.1'
    args = docopt(__doc__, version = version)

    path = args['<folder>']

    include = args['--include'].split(',')
    include = None if include==[''] else include
    ignore = args['--ignore'].split(',')
    ignore = [] if ignore==[''] else ignore
    add_sync = args['--add_sync'].split(',')
    add_sync = None if add_sync==[''] else int(add_sync)
    video_fps = args['--video_fps']

    if args['--video_recording_enable']:
      
      print('disable multi-threading')
      os.environ['QSG_RENDER_LOOP'] = "basic" #to set breakpoint in render thread...
      
    print(r"""
 ______              ____   ____  _                     
|_   _ `.           |_  _| |_  _|(_)                    
  | | `. \ ,--.   .--.\ \   / /  __  .---.  _   _   __  
  | |  | |`'_\ : ( (`\]\ \ / /  [  |/ /__\\[ \ [ \ [  ] 
 _| |_.' /// | |, `'.'. \ ' /    | || \__., \ \/\ \/ /  
|______.' \'-;__/[\__) ) \_/    [___]'.__.'  \__/\__/   
                                                        
      """)

    os.environ['QSG_RENDER_LOOP'] = "basic" #to set breakpoint in render thread...
    pf = platform.Platform(path, default_cache_size=1)
    v = Viewer(None, platform = pf, include=include, ignore=ignore, add_sync=add_sync, video_fps=video_fps)
    v.run()

if __name__ == "__main__":
    main()




