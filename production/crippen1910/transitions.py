"""Seven-frame (~0.3s) transitions with unshifted shot starts and exact total length.

Each outgoing normalized moving clip has seven extra frames obtained by a slight continuous
retime, not a frozen frame. Overlapping those handles preserves every original cut time.
"""
FPS=24
HANDLE_FRAMES=7
HANDLE=HANDLE_FRAMES/FPS
RADIO_CUTS={'S02','S19','S20','S22','S29','S30'}
SEA_CUTS={'S15','S16','S17','S18','S21','S23','S24','S25'}

def kind(shot_id):
    return 'radio_ring' if shot_id in RADIO_CUTS else 'wave' if shot_id in SEA_CUTS else 'fog'

def graph(shots):
    if not shots:raise ValueError('No motion clips')
    filters=[f'[{i}:v]settb=AVTB,setpts=PTS-STARTPTS[s{i}]' for i in range(len(shots))]
    current='s0';report=[]
    for i,shot in enumerate(shots[1:],1):
        mode=kind(shot['id']);target=f'x{i}';offset=float(shot['start'])
        if mode=='radio_ring':
            transition='transition=circleopen'
        elif mode=='wave':
            weight='clip(((1-P)*1.2-X/W-0.1+0.025*sin(Y/H*16+P*9))/0.10,0,1)'
            transition=f"transition=custom:expr='A*(1-({weight}))+B*({weight})'"
        else:
            transition="transition=custom:expr='clip(A*P+B*(1-P)+18*sin(PI*P),0,255)'"
        filters.append(f'[{current}][s{i}]xfade={transition}:duration={HANDLE:.9f}:offset={offset:.9f}[{target}]')
        report.append(dict(incoming=shot['id'],start=offset,frames=HANDLE_FRAMES,duration=HANDLE,kind=mode))
        current=target
    filters.append(f'[{current}]format=yuv420p[outv]')
    return ';\n'.join(filters),report
