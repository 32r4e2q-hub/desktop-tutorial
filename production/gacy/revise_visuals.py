"""Human-reviewed, non-graphic visual redesign authorized by the user.
No coded terms, hidden meanings, or automatic moderation retries.
Original documentary narration remains in story.json; this file designs only safe visible scenes.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STYLE = ('Cinematic stylized 3D animation of a fictional 1970s Midwestern neighborhood, '
         'warm amber practical lights and cool blue shadows, detailed period materials, '
         'subtle film grain and volumetric light, cinematic depth of field, widescreen 16:9. '
         'Characters and objects move naturally throughout a continuous animated shot. '
         'Compose the main subject on a vertical third with clear lower subtitle space. ')
ROLES = {
    '盖西': 'A fictional middle-aged adult man, fair skin, round clean-shaven face, stocky build, short light-brown hair, plain brown polo or dark suit. Three-quarter side or back view. ',
    '波戈': 'A fictional adult party entertainer, colorful one-piece costume, white theatrical face paint, red rounded nose, curly orange wig and colorful balloons; friendly restrained expression. ',
    '少年': 'Every younger figure appears only from behind as an anonymous silhouette, wearing a period denim jacket, jeans, sneakers and a small backpack. ',
    '母亲': 'An adult woman in her forties, brown curly hair, dark wool coat, dignified and thoughtful. ',
    '警探': 'Adult investigators wear period trench coats and felt hats; calm focused body language. ',
    '法官与陪审团': 'An adult judge wears a traditional black robe; adult jurors wear period formal clothing. ',
}
SCENES = [
    'One wide exterior at night: neat white houses, a lit window and amber streetlamps. A red balloon drifts gently above a rooftop while branches and thin mist move. The aerial camera descends smoothly toward the window. Hold this single neighborhood view for the full clip.',
    'One abstract study of a wooden floor meeting a dark shaft of light: warm light softly diminishes as the camera lowers toward the edge of a floorboard. Tiny dust particles drift freely in the cool light. The visible elements are wood grain, light and airborne dust only. Hold this one continuous composition.',
    'One neighborhood party in a garden: the adult entertainer folds a colorful balloon with both hands while anonymous younger figures seen strictly from behind clap softly at the edge of frame. Streamers flutter and balloons sway. One slow wide camera arc, remaining at this garden throughout.',
    'One quiet room with a bed and golden window light: an adult entertainer twists a balloon animal beside an anonymous seated younger figure seen entirely from behind. The hands and balloon move naturally; curtains flutter. One slow medium camera approach, remaining inside this room.',
    'One dressing room mirror composition: the stocky adult man gently removes an orange wig and rests it on a plain counter. Amber bulbs illuminate one side of his face and cool shadows the other. His hands, shoulders and reflection move consistently. One slow close approach.',
    'One reception room: a fictional adult hostess and several adult guests adjust their posture for a group photograph, the stocky adult man among them. A flash briefly lights the room while fabric and people continue moving. Period formal clothes and plain decorations. One fixed medium camera.',
    'Inside one wood-panelled courtroom, an adult judge in a black robe lowers a wooden gavel once onto a desk. A seated adult is visible only from behind at the side of frame. Soft cool daylight, quiet formal atmosphere. One gentle approach, remaining inside the courtroom.',
    'Inside one long institutional corridor, an adult man carrying a small plain travel bag walks calmly through an opening doorway into bright winter daylight. His coat and bag swing naturally as his shadow travels over the floor. One continuous back-following camera move.',
    'Outside one neat suburban home, an adult man plants a small plain unlettered wooden board beside a flowerbed. An adult neighbor waves from a distance, and the man returns the wave. Leaves move in warm sunshine. One slow medium pullback.',
    'One evening bus-stop composition: an anonymous younger figure, seen strictly from behind, walks beyond frame. An empty bench remains; loose blank paper slides lightly across the pavement in the breeze. One fixed wide camera, holding this single setting.',
    'One close view of a community noticeboard covered with plain unlettered paper and soft abstract silhouette-shaped illustrations. Rain beads on the surface and a few paper corners flutter gently. One slow horizontal camera move, staying close enough that the board fills the frame.',
    'One home interior: the woman waits beside a cool-blue window with a plain framed silhouette photograph and a glass of milk on a table. She walks to a ringing rotary telephone, listens, then quietly sets the receiver down. One medium fixed view of this single room.',
    'One tidy garden outside a white house: an adult neighbor pauses to adjust a scarf against the wind, while the stocky man gives a small welcoming wave beside a hedge. Leaves and flower stems sway naturally. One restrained low-angle camera movement.',
    'Outside one small period shop at night, the woman waits under an awning and checks her wristwatch. Snowflakes settle on her dark coat; warm window light contrasts with the cold blue street. The shop window has plain unlettered glass. One slow camera approach.',
    'Inside one warmly lit shop, an anonymous younger figure seen entirely from behind removes a plain work apron, waves to the woman and steps through the door into softly falling snow. The door and its small brass bell swing naturally. One rear-following camera move.',
    'One snowy street at night: an unoccupied view of a period vehicle rolling away in the far distance, while the woman waits beneath an amber streetlamp at the right third. Snow and coat fabric move gently. The aerial camera rises slowly, keeping this street in view.',
    'Inside one quiet interview office, the woman sits opposite an adult investigator who writes carefully in a plain notebook. Steam rises from a cup, and an unnumbered wall clock ticks. Both adults make small natural gestures. One slow medium camera approach.',
    'Inside one workroom, adult investigators study a plain map covered with simple colored pins and thread. One investigator places a final pin while another follows a connection with a finger. A desk lamp casts warm light. One continuous overhead camera move.',
    'One quiet evening street: two ordinary period cars travel along a residential road at a safe distance. Wheels turn, soft headlights pass trees and reflections move over damp pavement. One smooth low tracking camera, keeping this road in view.',
    'At one suburban doorway, two adult investigators present a plain folder. The stocky man opens the door and steps aside; the visitors enter a warmly lit living room. Calm ordinary gestures, period clothing and intact household objects. One continuous doorway camera approach.',
    'An abstract first-person flashlight composition: a cool light beam travels gently over dark wooden boards and airborne dust. The beam swings slowly as if carried by a walking observer. Only the boards, light and freely drifting particles are visible. One continuous restrained forward move.',
    'One abstract dark composition: a slim shaft of cool light widens gradually while tiny dust particles drift at different depths. The camera lowers gently through the illuminated air. The entire image consists of black space, a light beam and independently moving particles.',
    'One wide exterior of a winter garden at night: adult field workers calmly set up plain white weather shelters while soft blue work lights reflect across the snow. A few adults wait outside a simple rope boundary. One slow rising aerial view, holding this single location.',
    'One winter river surface: a small work boat moves slowly across rippling water while reflected searchlights sweep over the surface. The camera lowers toward the ripples until blue water and floating particles fill the view. One smooth continuous camera movement.',
    'Inside one formal wood-panelled courtroom, an adult man seen from behind raises one hand while addressing seated adult jurors. The jurors listen and turn their heads subtly. A black-robed judge sits in the background. One restrained wide camera arc inside this room.',
    'Inside one quiet institutional corridor, overhead lamps dim one by one as the camera slowly withdraws. A single adult staff member walks calmly across a distant doorway. Cool gray walls and simple metal doors. Hold this corridor for the full clip.',
    'One artist worktable in a small plain room: a colorful theatrical-entertainer painting rests on an easel while an adult hand turns blank pages of a desk calendar. Window light slowly shifts across the painted canvas. One fixed medium camera, remaining inside this room.',
    'One peaceful memorial garden at dusk: an older adult woman seen only as a back silhouette gently places a white flower beside plain unlettered stones. Leaves and flower stems move in the breeze. One low slow camera approach, with a respectful quiet composition.',
]
GUARD = ('Visible content is limited to fully clothed fictional stylized people, calm gestures, '
         'period props and intact environments. Younger figures remain anonymous back silhouettes. '
         'Props and surfaces are plain and unlettered. Maintain one consistent 3D style and '
         'continuous physical motion in this single scene. ')


def build():
    original = json.loads((HERE/'story.json').read_text())
    shots = {}
    for shot, scene in zip(original['shots'][:-1], SCENES):
        roles = ''.join(ROLES[r] for r in shot['roles'])
        shots[shot['id']] = {'prompt':STYLE+roles+scene+' '+GUARD,
            'roles':shot['roles'], 'scene':scene, 'original_start':shot['start'],
            'original_end':shot['end'], 'safety_review':'non-graphic visual redesign; provider approval not guaranteed'}
    output={'revision':'non_graphic_visual_revision_2','authorized_by':'user permitted all revisions on this turn',
        'style':STYLE,'roles':ROLES,'shots':shots,
        'source_reference':'maryceleste1872@git branch arena/63ceeca2-desktop-tutorial',
        'provider_payload_keys':['model','prompt','quality'],
        'limitations':['text descriptions do not guarantee actor-level identity consistency',
            'moderation rejection is terminal for that revision; no automatic evasion or repeated resubmission'],
        'editorial_changes':['S13 uses ordinary neighbor gestures rather than a smell effect',
            'S21/S22 use abstract moving light and dust, with no physical discovery reenactment',
            'S26 is one continuous corridor shot rather than multiple actions in a single generation',
            'all text, dates and documentary context are retained for post-production narration/captions']}
    (HERE/'visual-plan.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
    build()
