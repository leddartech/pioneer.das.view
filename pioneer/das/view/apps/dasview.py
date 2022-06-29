"""dasview

Usage:
  dasview <folder>
  dasview <folder> [options]
  dasview (-h | --help | --version)
  Use --help for more info

Options:
-h, --help               show this help message and exit
  --version              show version and exit
  --include=<inc>        exclusively included sensors in platform [default: ]
  --ignore=<ign>         ignored sensors in platform [default: ]
  --add_sync=<source>    given source will also be synchronized [default: ]
  --video_recording_enable        desactivate the qt multi-threading, and then enable frame grabing for video recording
  --video_fps=<int>      force video fps to a specific value, else compute from datasource timestamps
-l, --log                activate das.api logger
"""

from pioneer.das.api import platform
from pioneer.das.view.viewer import Viewer

import docopt
import os

DEFAULT_IGNORE_LABELS = ['radarTI_bfc']

def main():
    import os
    version = '1.4.0'

    try:
      args = docopt.docopt(__doc__, version = f'dasview {version}')
    except docopt.DocoptExit as e:
      print(e)
      exit()

    path = args['<folder>']

    include = args['--include'].split(',')
    include = None if include==[''] else include
    ignore = args['--ignore'].split(',')
    ignore = [] if ignore==[''] else ignore
    add_sync = args['--add_sync'].split(',')
    add_sync = None if add_sync==[''] else int(add_sync)
    video_fps = args['--video_fps']
    use_logger = args['--log']

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
    pf = platform.Platform(path, default_cache_size=1, activate_logger=use_logger)
    v = Viewer(None, platform = pf, include=include, ignore=ignore, add_sync=add_sync, video_fps=video_fps)
    v.run()

if __name__ == "__main__":
    main()




