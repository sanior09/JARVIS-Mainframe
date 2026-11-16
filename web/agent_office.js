/* ==========================================================================
   NACHAPOL INDUSTRIES // AI OFFICE (HYBRID 2.5D PIXEL LAB + BENTO OPS DECK)
   ========================================================================== */

(function () {
    'use strict';

    const OFFICE_W = 1376;
    const OFFICE_H = 768;
    const POLL_MS = 1200;
    const SPRITE_SCALE = 1.65;

    const SHARED_ROOM_SLOTS = {
        intel_lab: [
            { x: 228, y: 258, dir: 'up', sit: true, mon: { x: 242, y: 189, w: 46, h: 28 } },
            { x: 416, y: 258, dir: 'up', sit: true, mon: { x: 422, y: 188, w: 42, h: 28 } },
            { x: 110, y: 248, dir: 'left', sit: true, mon: { x: 48, y: 204, w: 26, h: 24 } },
        ],
        command_deck: [
            { x: 710, y: 152, dir: 'down', sit: true, mon: { x: 740, y: 150, w: 40, h: 24 } },
            { x: 644, y: 248, dir: 'up', sit: true, mon: { x: 616, y: 92, w: 140, h: 48 } },
            { x: 750, y: 248, dir: 'up', sit: true, mon: { x: 740, y: 150, w: 40, h: 24 } },
        ],
        dev_lab: [
            { x: 1152, y: 252, dir: 'up', sit: true, mon: { x: 1114, y: 156, w: 76, h: 40 } },
            { x: 970, y: 252, dir: 'up', sit: true, mon: { x: 914, y: 152, w: 62, h: 38 } },
            { x: 1292, y: 252, dir: 'up', sit: true, mon: { x: 1272, y: 168, w: 54, h: 32 } },
        ],
        data_net: [
            { x: 306, y: 496, dir: 'up', sit: true, mon: { x: 264, y: 432, w: 40, h: 26 } },
            { x: 162, y: 496, dir: 'up', sit: true, mon: { x: 138, y: 432, w: 38, h: 26 } },
            { x: 334, y: 418, dir: 'up', sit: false, mon: { x: 248, y: 318, w: 126, h: 68 } },
        ],
        maker_iot: [
            { x: 1062, y: 456, dir: 'up', sit: true, mon: { x: 918, y: 378, w: 46, h: 42 } },
            { x: 978, y: 514, dir: 'up', sit: false, mon: { x: 982, y: 378, w: 46, h: 42 } },
            { x: 1288, y: 492, dir: 'up', sit: true, mon: { x: 1282, y: 422, w: 36, h: 26 } },
        ],
        sys_ops: [
            { x: 444, y: 704, dir: 'up', sit: true, mon: { x: 396, y: 636, w: 80, h: 24 } },
            { x: 290, y: 698, dir: 'up', sit: true, mon: { x: 274, y: 632, w: 46, h: 28 } },
            { x: 138, y: 698, dir: 'up', sit: true, mon: { x: 134, y: 618, w: 48, h: 28 } },
        ],
        media_qa: [
            { x: 964, y: 686, dir: 'right', sit: true, mon: { x: 1208, y: 610, w: 56, h: 52 } },
            { x: 1100, y: 686, dir: 'left', sit: true, mon: { x: 1208, y: 610, w: 56, h: 52 } },
            { x: 1178, y: 688, dir: 'right', sit: false, mon: { x: 1208, y: 610, w: 56, h: 52 } },
        ],
    };

    const LEGACY_ROOM_MAP = {
        desk_edith: 'intel_lab',
        desk_jarvis: 'command_deck',
        desk_karen: 'sys_ops',
        desk_veronica: 'dev_lab',
        desk_friday: 'dev_lab',
        desk_dume: 'maker_iot',
        desk_jocasta: 'data_net',
        desk_u: 'media_qa',
    };

    const MEETING_SEATS = {
        friday: { x: 616, y: 488, dir: 'down', sit: true },
        jarvis: { x: 660, y: 488, dir: 'down', sit: true },
        veronica: { x: 704, y: 488, dir: 'down', sit: true },
        edith: { x: 572, y: 530, dir: 'right', sit: false },
        dume: { x: 660, y: 576, dir: 'up', sit: false },
        karen: { x: 752, y: 486, dir: 'right', sit: true },
        jocasta: { x: 828, y: 486, dir: 'left', sit: true },
        u: { x: 790, y: 526, dir: 'up', sit: true },
    };

    const CHILL_SEATS = [
        { x: 616, y: 488, dir: 'down', sit: true },  // Green sofa left
        { x: 660, y: 488, dir: 'down', sit: true },  // Green sofa center
        { x: 704, y: 488, dir: 'down', sit: true },  // Green sofa right
        { x: 752, y: 486, dir: 'right', sit: true }, // Round bistro left chair
        { x: 828, y: 486, dir: 'left', sit: true },  // Round bistro right chair
        { x: 790, y: 526, dir: 'up', sit: true },    // Round bistro stool
        { x: 644, y: 248, dir: 'up', sit: true },    // Command visitor armchair L
        { x: 750, y: 248, dir: 'up', sit: true },    // Command visitor armchair R
    ];

    const LOUNGE_SPOTS = [
        { x: 598, y: 432, dir: 'up', sit: false },   // Espresso bar left
        { x: 695, y: 434, dir: 'up', sit: false },   // Espresso bar center
        { x: 636, y: 596, dir: 'down', sit: false }, // Central lobby
        { x: 742, y: 602, dir: 'down', sit: false }, // East lobby
        { x: 695, y: 666, dir: 'down', sit: false }, // Welcome mat
        { x: 695, y: 318, dir: 'down', sit: false }, // Command balcony
        { x: 572, y: 336, dir: 'down', sit: false }, // North atrium left
        { x: 836, y: 336, dir: 'down', sit: false }, // North atrium right
    ];

    const ROAM_ROOM_POOL = [
        'chill_seat', 'chill_seat', 'chill_seat',
        'lounge', 'lounge',
        'intel_lab', 'command_deck', 'dev_lab',
        'data_net', 'maker_iot', 'sys_ops', 'media_qa',
    ];

    const ROOM_LABELS = {
        intel_lab: 'INTEL LAB',
        command_deck: 'COMMAND DECK',
        dev_lab: 'UI & DEV LAB',
        data_net: 'DATA / NET',
        maker_iot: 'IOT & MAKER',
        sys_ops: 'SYS OPS',
        media_qa: 'MEDIA & QA',
        meeting: 'BRIEFING LOUNGE',
        lounge: 'ATRIUM & COFFEE BAR',
    };

    // High-Detail 2D Pixel Art Character Cast (colored 1px outlines + custom palettes)
    // Core 5 extracted & quantized cleanly from the user's 2D pixel reference, plus matching Veronica/Jocasta/Karen.
    const PIXEL_CAST = {
        edith: {
            bracket: "//E.D.I.T.H.//",
            palette: { "A": '#2eb3f8', "B": '#100984', "C": '#fa6743', "D": '#f6dceb', "E": '#d0f4ff', "F": '#4d0255', "G": '#2d5dce', "H": '#e1696a', "I": '#210466', "J": '#5c4c93', "K": '#48a6fc', "L": '#c86a85', "M": '#65002c', "N": '#c8bbee', "O": '#a8dafd', "P": '#003391', "Q": '#608bef', "R": '#0063bf' },
            rows: [
                '...III....................',
                '..IHCCF...................',
                '..HCCCHIBBBIIII...........',
                'BHCCCCIKKBHCCCCF..........',
                'BHCCHIKKBHCCCCCCF.........',
                'BHCC.KKBLCCCCCCCCF........',
                '.ILIKKBHCCCIIILCCCF.......',
                '..IBKBLCCCFDDDILCCCM......',
                '...BIHCCCIBBBDBBBBLCF.....',
                '...BLCCCFEEEEIEEEEILFI....',
                '...BLCC.EEIEEBEBEEE.......',
                '....IHCIBEEEIDIEEEBB...B..',
                '.....IHHIBBBDDDIBB....NDJ.',
                '.....BLCFDDDIIDDBI..IQODJI',
                '.......IBDDDDDDI....KKPB..',
                '.........IBBBBB...IQAPI...',
                '.....BBBBKBNDBKBBBKKPI....',
                '....IKKKKABDDIKAKKAP......',
                '...IKABBKABBBBAAAPBI......',
                '..IKKBIBKAKBKKAAPI........',
                '..BKB..BKAABKAAABI........',
                '..BKAB.BKAABKAAAB.........',
                '...BKBBBKAABKAAABI........',
                '....BDDBBAABKAAR..........',
                '.....IDBKAPBBBKAB.........',
                '......IBKAKKKKAAB.........',
                '.......BKAAAAAAAB.........',
                '.......BKAAAAAAAB.........',
                '.......BKAAAAAAAB.........',
                '.......BKAPBBPKAB.........',
                '.......BKABI.BKAB.........',
                '.......BKAB..IKAB.........',
                '.......BKAB..BKAB.........',
                '.......BKAB..IKAB.........',
                '.......BGGB..IGGB.........',
                '.......GGGB..BGGGB........',
                '......IGGGB..BGGGB........',
            ],
            up: [
                '.......FFFFF......',
                '......FCCCCCF.....',
                '......FCCCCCF.....',
                '.....BAAAAAAAB....',
                '.....FCCCCCCCF....',
                '.....FCHHHHHCF....',
                '....FCCHHHHHCCF...',
                '....FCCCCCCCCCF...',
                '...BDCCCCCCCCCDB..',
                '....FCCCCCCCCCF...',
                '....FCCCCCCCCCF...',
                '....FCCCCCCCCCF...',
                '....FCCCCCCCCCF...',
                '.....FFDDDDFFF....',
                '......BDDDDB......',
                '......BLLLLB......',
                '.....BBLLLLBBB....',
                '...BBRRRRRRRRRBB..',
                '..BRRRRRRRRRRRRRB.',
                '..BRRAAAARAAAARRB.',
                '..BRRAAAARAAAARRB.',
                '..BRRAAAARAAAARRB.',
                '..BRRAAAARAAAARRB.',
                '..BRRAAAARAAAARRB.',
                '..BRRAAAARAAAARRB.',
                '..BRRAAAARAAAARRB.',
                '..BRRAAAARAAAARRB.',
                '..BDDPPPPPPPPPDDB.',
                '..BDDPPPPPPPPPDDB.',
                '...BBBAABBAABBBB..',
                '.....BAABBAAB.....',
                '.....BAABBAAB.....',
                '.....BAABBAAB.....',
                '.....BAABBAAB.....',
                '.....BGGBBGGB.....',
                '.....BGGBBGGB.....',
                '......BB..BB......',
            ],
            sideIdle: [
                '....FFFF............',
                '...FCCCCF...........',
                '...FCCAAB...........',
                '...FCCAAFFFFF.......',
                '...FCCCCHHHHCF......',
                '....FFCCHHHHCF......',
                '....FCCCCCCCCDB.....',
                '....FCCCDDDEEEB.....',
                '....FCCCDADEBEB.....',
                '....FCCCCDDEEEDB....',
                '....FCCCDDDDDDB.....',
                '....FCCCDDDDLDB.....',
                '.....FFDDDDDDDB.....',
                '.......BBBBBBB......',
                '........BBBB........',
                '.......BLLLLB.......',
                '.......BLLLLBB......',
                '......BAAAAAAAB.....',
                '......BAAAAAAAB.....',
                '......BABRAAAAB.....',
                '......BABRAAAAB.....',
                '......BABRAAAAB.....',
                '......BABRAAAAB.....',
                '......BABRAAAAB.....',
                '......BABRAAAAB.....',
                '......BABRAAAAB.....',
                '......BABRAAAAB.....',
                '......BPBDDPPPB.....',
                '......BPBDDPPPB.....',
                '.......BAAAABB......',
                '.......BAAAAB.......',
                '.......BAAAAB.......',
                '.......BAAAAB.......',
                '.......BAAAAB.......',
                '.......BGGGGGB......',
                '.......BGGGGGB......',
                '........BBBBB.......',
            ],
            sideWalkA: [
                '...FCCCCF...........',
                '...FCCAAB...........',
                '...FCCAAFFFFF.......',
                '...FCCCCHHHHCF......',
                '....FFCCHHHHCF......',
                '....FCCCCCCCCDB.....',
                '....FCCCDDDEEEB.....',
                '....FCCCDADEBEB.....',
                '....FCCCCDDEEEDB....',
                '....FCCCDDDDDDB.....',
                '....FCCCDDDDLDB.....',
                '.....FFDDDDDDDB.....',
                '.......BBBBBBB......',
                '........BBBB........',
                '.......BLLLLB.......',
                '.......BLLLLBB......',
                '......BAAAAAAAB.....',
                '......BAAAAAAAB.....',
                '......BABRAAAAB.....',
                '......BABRAAAAB.....',
                '......BBRAAAAAB.....',
                '......BBRAAAAAB.....',
                '......BBRAAAAAB.....',
                '.....BBRAAAAAAB.....',
                '.....BBRAAAAAAB.....',
                '.....BBRAAAAAAB.....',
                '....BBDDPPPPPPB.....',
                '....BBDDPPPPPPB.....',
                '.....BBBBAAABB......',
                '........BAAAB.......',
                '.......BRRAAAB......',
                '......BRRRBAAAB.....',
                '......BRRRBAAAB.....',
                '.....BGGGGBAAABB....',
                '.....BGGGGBBGGGGB...',
                '......BBBB.BGGGGB...',
                '............BBBB....',
            ],
            sideWalkB: [
                '...FCCCCF...........',
                '...FCCAAB...........',
                '...FCCAAFFFFF.......',
                '...FCCCCHHHHCF......',
                '....FFCCHHHHCF......',
                '....FCCCCCCCCDB.....',
                '....FCCCDDDEEEB.....',
                '....FCCCDADEBEB.....',
                '....FCCCCDDEEEDB....',
                '....FCCCDDDDDDB.....',
                '....FCCCDDDDLDB.....',
                '.....FFDDDDDDDB.....',
                '.......BBBBBBB......',
                '........BBBB........',
                '.......BLLLLB.......',
                '.......BLLLLBB......',
                '......BAAAAAAAB.....',
                '......BAAAAAAAB.....',
                '......BABRAAAAB.....',
                '......BABRAAAAB.....',
                '......BAABRAAAB.....',
                '......BAABRAAAB.....',
                '......BAABRAAAB.....',
                '......BAAABRAAB.....',
                '......BAAABRAAB.....',
                '......BAAABRAAB.....',
                '......BPPPPBDDB.....',
                '......BPPPPBDDB.....',
                '.......BBAAABB......',
                '........BAAAB.......',
                '.......BAAARRB......',
                '......BAAABRRRB.....',
                '......BAAABRRRB.....',
                '.....BGGGGBRRRBB....',
                '.....BGGGGBBGGGGB...',
                '......BBBB.BGGGGB...',
                '............BBBB....',
            ],
        },
        jarvis: {
            bracket: "[[J.A.R.V.I.S.]]",
            palette: { "A": '#089ca3', "B": '#043c5f', "C": '#00647a', "D": '#f2deda', "E": '#28425c', "F": '#b27844', "G": '#e4f8ff', "H": '#121e46', "I": '#11738b', "J": '#494140', "K": '#9e7756', "L": '#7d7260', "M": '#4f6678', "N": '#c5d6e1' },
            rows: [
                '.....BEEBEH.....',
                '...HJFFFFFFB....',
                '..EFKKKFFFFBH...',
                '..EFLBEKFKKJLE..',
                '..JKEDDHBHBDBB..',
                '.EFKEDDDDDDDBB..',
                'HEFFEDDDDDDNBB..',
                '.EKLEDBEDDBBB...',
                '..BBEDGEDDBGB...',
                '..EDEDGEDDEGB...',
                '..EDDDDDDDDDB...',
                '...BEDDDBBDDB...',
                '.....EDDDDDH....',
                '......BBBBH.....',
                '.....EGEDBGB....',
                '...BBBEGBGBBB...',
                'HBBAAABBABBAABB.',
                'CIBAAAEGAGBAABBB',
                'CAIBAABBABBAABAB',
                'CAABAABBBBBAABAB',
                'CAABAABABABAABAB',
                'CAABAABABABAABAB',
                'CAABAABABABAABAB',
                'CAABAABABABAABAB',
                'CAABAABABABAABAB',
                'CAABAABABABAABAB',
                'CAABAABABABAABAB',
                'CAABAABCIBBAABAB',
                'MDNBAABAAABAABNB',
                'MDNBAABAAABAABDB',
                'HBIAAABAAABAAIE.',
                '.HCAACIBBCICAAB.',
                '..BAABABHBABAAB.',
                '..BAABAB.BABAAB.',
                '..BBCAAB.BAIBBB.',
                '...HBAAB.BAAB...',
                '....BAAB.BAAB...',
                '....BAAB.BAAB...',
                '....BAAB.BAAB...',
                '....BAAB.BAAB...',
                '....BAAB.BAAB...',
                '....BAAB.BAAB...',
                '....BAAB.BAAB...',
                '...HBICB.BICB...',
                '..BIIICB.BIIIIH.',
                '..BIIICB.BIIIIB.',
            ],
            up: [
                '......BBBBBBB.....',
                '.....BFFFFFFFB....',
                '.....BFKKKKKFB....',
                '....BFFKKKKKFFB...',
                '....BFFFFFFFFFB...',
                '...BDFFFFFFFFFDB..',
                '....BFFFFFFFFFB...',
                '....BFFFFFFFFFB...',
                '....BFFFFFFFFFB...',
                '....BFFFFFFFFFB...',
                '....BFFFFFFFFFB...',
                '....BFFFFFFFFFB...',
                '.....BBDDDDBBB....',
                '......BDDDDB......',
                '......BNNNNB......',
                '....BBBNNNNBBB....',
                '..BBCCCCCCCCCCBB..',
                '.BCCCCCCCCCCCCCCB.',
                '.BCCAAAAACAAAACCB.',
                '.BCCAAAAACAAAACCB.',
                '.BCCAAAAACAAAACCB.',
                '.BCCAAAAACAAAACCB.',
                '.BCCAAAAACAAAACCB.',
                '.BCCAAAAACAAAACCB.',
                '.BCCAAAAACAAAACCB.',
                '.BCCAAAAACAAAACCB.',
                '.BCCAAAAACAAAACCB.',
                '.BCCAAAAACAAAACCB.',
                '.BCCAAAAACAAAACCB.',
                '.BCCAAAAACAAAACCB.',
                '.BCCAAAAACAAAACCB.',
                '.BDDBBBBBBBBBBDDB.',
                '.BDDBBBBBBBBBBDDB.',
                '..BBCCCCCCCCCCBB..',
                '...BCCCCCBCCCCB...',
                '....BBAABBAABB....',
                '.....BAABBAAB.....',
                '.....BAABBAAB.....',
                '.....BAABBAAB.....',
                '.....BAABBAAB.....',
                '.....BAABBAAB.....',
                '.....BAABBAAB.....',
                '.....BAABBAAB.....',
                '.....BIIBBIIB.....',
                '.....BIIBBIIB.....',
                '......BB..BB......',
            ],
            sideIdle: [
                '......BBBBBBB.......',
                '.....BFFKKKKFB......',
                '.....BFFKKKKFB......',
                '....BFFFFFFFFDB.....',
                '....BFFFDDDDDDB.....',
                '....BFFFDDDDBDB.....',
                '....BFFFFDDDBDDB....',
                '....BFFFDDDDDDB.....',
                '....BFFFDDDDDDB.....',
                '....BFFFDDDDDDB.....',
                '....BFFFDDDDNDB.....',
                '.....BBDDDDDDDB.....',
                '.......BBBBBBB......',
                '........BBBB........',
                '.......BNNNNB.......',
                '.......BNNNNBB......',
                '......BAAAAAGGB.....',
                '......BAAAAAGAB.....',
                '......BABCAAGAB.....',
                '......BABCAAGAB.....',
                '......BABCAAGAB.....',
                '......BABCAAAAB.....',
                '......BABCAAAAB.....',
                '......BABCAAAAB.....',
                '......BABCAAAAB.....',
                '......BABCAAAAB.....',
                '......BABCAAAAB.....',
                '......BABCAAAAB.....',
                '......BABCAAAAB.....',
                '......BABCAAAAB.....',
                '......BABCAAAAB.....',
                '......BBBDDBBBB.....',
                '......BBBDDBBBB.....',
                '.....BCCCCCCCCB.....',
                '.....BCCCCCCCCB.....',
                '......BBAAAABB......',
                '.......BAAAAB.......',
                '.......BAAAAB.......',
                '.......BAAAAB.......',
                '.......BAAAAB.......',
                '.......BAAAAB.......',
                '.......BAAAAB.......',
                '.......BAAAAB.......',
                '.......BIIIIIB......',
                '.......BIIIIIB......',
                '........BBBBB.......',
            ],
            sideWalkA: [
                '.....BFFKKKKFB......',
                '.....BFFKKKKFB......',
                '....BFFFFFFFFDB.....',
                '....BFFFDDDDDDB.....',
                '....BFFFDDDDBDB.....',
                '....BFFFFDDDBDDB....',
                '....BFFFDDDDDDB.....',
                '....BFFFDDDDDDB.....',
                '....BFFFDDDDDDB.....',
                '....BFFFDDDDNDB.....',
                '.....BBDDDDDDDB.....',
                '.......BBBBBBB......',
                '........BBBB........',
                '.......BNNNNB.......',
                '.......BNNNNBB......',
                '......BAAAAAGGB.....',
                '......BAAAAAGAB.....',
                '......BABCAAGAB.....',
                '......BABCAAGAB.....',
                '......BABCAAGAB.....',
                '......BBCAAAAAB.....',
                '......BBCAAAAAB.....',
                '......BBCAAAAAB.....',
                '......BBCAAAAAB.....',
                '.....BBCAAAAAAB.....',
                '.....BBCAAAAAAB.....',
                '.....BBCAAAAAAB.....',
                '.....BBCAAAAAAB.....',
                '.....BBCAAAAAAB.....',
                '....BBCAAAAAAAB.....',
                '....BBDDBBBBBBB.....',
                '....BBDDBBBBBBB.....',
                '.....BCCCCCCCCB.....',
                '.....BCCCCCCCCB.....',
                '......BBBAAABB......',
                '........BAAAB.......',
                '.......BCCAAAB......',
                '.......BCCAAAB......',
                '.......BCCAAAB......',
                '......BCCCBAAAB.....',
                '......BCCCBAAAB.....',
                '......BCCCBAAAB.....',
                '.....BIIIIBBAAAB....',
                '.....BIIIIBBIIIIB...',
                '......BBBB.BIIIIB...',
                '............BBBB....',
            ],
            sideWalkB: [
                '.....BFFKKKKFB......',
                '.....BFFKKKKFB......',
                '....BFFFFFFFFDB.....',
                '....BFFFDDDDDDB.....',
                '....BFFFDDDDBDB.....',
                '....BFFFFDDDBDDB....',
                '....BFFFDDDDDDB.....',
                '....BFFFDDDDDDB.....',
                '....BFFFDDDDDDB.....',
                '....BFFFDDDDNDB.....',
                '.....BBDDDDDDDB.....',
                '.......BBBBBBB......',
                '........BBBB........',
                '.......BNNNNB.......',
                '.......BNNNNBB......',
                '......BAAAAAGGB.....',
                '......BAAAAAGAB.....',
                '......BABCAAGAB.....',
                '......BABCAAGAB.....',
                '......BABCAAGAB.....',
                '......BAABCAAAB.....',
                '......BAABCAAAB.....',
                '......BAABCAAAB.....',
                '......BAABCAAAB.....',
                '......BAAABCAAB.....',
                '......BAAABCAAB.....',
                '......BAAABCAAB.....',
                '......BAAABCAAB.....',
                '......BAAABCAAB.....',
                '......BAAAABCAB.....',
                '......BBBBBBDDB.....',
                '......BBBBBBDDB.....',
                '.....BCCCCCCCCB.....',
                '.....BCCCCCCCCB.....',
                '......BBBAAABB......',
                '........BAAAB.......',
                '.......BAAACCB......',
                '.......BAAACCB......',
                '.......BAAACCB......',
                '......BAAABCCCB.....',
                '......BAAABCCCB.....',
                '......BAAABCCCB.....',
                '.....BIIIIBBCCCB....',
                '.....BIIIIBBIIIIB...',
                '......BBBB.BIIIIB...',
                '............BBBB....',
            ],
        },
        friday: {
            bracket: "(F.R.I.D.A.Y.)",
            palette: { "A": '#f44204', "B": '#fe9942', "C": '#7a0530', "D": '#31002a', "E": '#ffd6dc', "F": '#e54120', "G": '#bb2424', "H": '#ffefff', "I": '#8c031e', "J": '#570529', "K": '#fd955d', "L": '#c86a85' },
            rows: [
                '......DCIIICD......',
                '...DCCCKBBBBICD....',
                '...CBBBBBKKBBBID...',
                '..CKBBBBBCCKBBBCD..',
                '..CBBBBKCEECKBBCD..',
                '..CBBBKJCCECCKBCD..',
                '.CKBKKCEEEEEECKCD..',
                '.CBBCCCCCCECJCKCD..',
                '.CBBCEJHJCECHCCD...',
                '.CBBCEEEEEEEECD....',
                '.CBBKIEEEJCEECD....',
                '.DCKBKIEEEEEJKID...',
                '..CKBBKCJCCCKBBCD..',
                '.CKBBBBCEECKBBBCD..',
                '.CCKBBICFFIIKBBID..',
                '..DCIIFIEECFIICD...',
                '...CFFAAICFAFFID...',
                '..CFAIAAFIFAIAACD..',
                '.CFAIIAAACAAICFFI..',
                'CFAIDCAAAIFAIDCAFCD',
                'CFID.CIIICIIC..IFID',
                'CFFJ.CFFCCCFI.JFAID',
                'DIAFJCIIICCICJFFID.',
                '.DCEECFFFFFFIEEIJ..',
                '..DCECFAAAAAIECD...',
                '...CCFAAAAAAFICD...',
                '...CFAAAAAAAAFC....',
                '...CAAAAAAAAAAI....',
                '...CAAAAAAAAAAID...',
                '..JFAAAAAAAAAAFCD..',
                '..CFAAAAAAAAAAAID..',
                '..CAAAAAAAAAAAAID..',
                '..CFAAAAAAAAAAAID..',
                '..JIIIIIIIIIIIIJ...',
                '...DDDCGFCGFCJD....',
                '......CFACFAI......',
                '......CFAIFAI......',
                '......CGGCGGID.....',
                '.....JGGGCGGGJD....',
                '.....CGGGCGGGC.....',
            ],
            up: [
                '......IIIIIII.....',
                '.....IBBBBBBBI....',
                '.....IBKKKKKBI....',
                '....IBBKKKKKBBI...',
                '....IBBBBBBBBBI...',
                '...CEBBBBBBBBBEC..',
                '....IBBBBBBBBBI...',
                '....IBBBBBBBBBI...',
                '....IBBBBBBBBBI...',
                '....IBBBBBBBBBI...',
                '....IBBBBBBBBBI...',
                '....IBBBBBBBBBI...',
                '....IBBBBBBBBBI...',
                '....IBKKKKKKKBI...',
                '....IBKKKKKKKBI...',
                '....IBKLLLLKKBI...',
                '....IBBLLLLBBBI...',
                '...CCFFFFFFFFFCC..',
                '..CFFFFFFFFFFFFFC.',
                '..CFFAAAAFAAAAFFC.',
                '..CFFAAAAFAAAAFFC.',
                '..CFFAAAAFAAAAFFC.',
                '..CFFAAAAFAAAAFFC.',
                '..CEECCCCCCCCCEEC.',
                '..CEECCCCCCCCCEEC.',
                '...CAAAAAAAAAAAC..',
                '...CAAAAAAAAAAAC..',
                '...CAAAAAAAAAAAC..',
                '...CAAAAAAAAAAAC..',
                '...CAAAAAAAAAAAC..',
                '...CAAAAAAAAAAAC..',
                '...CAAAAAAAAAAAC..',
                '...CFFFFFFFFFFFC..',
                '...CFFFFFFFFFFFC..',
                '....CCAACCAACCC...',
                '.....CAACCAAC.....',
                '.....CAACCAAC.....',
                '.....CGGCCGGC.....',
                '.....CGGCCGGC.....',
                '......CC..CC......',
            ],
            sideIdle: [
                '......IIIIIII.......',
                '.....IBBKKKKBI......',
                '....IIBBKKKKBI......',
                '...IBBBBBBBBBEC.....',
                '...IBBBBEEEEEEC.....',
                '...IBBBBEEEEJEC.....',
                '...IBBBBBEEEJEEC....',
                '...IBKKBEEEEEEC.....',
                '...IBKKBEEEEEEC.....',
                '...IBKKBEEEEEEC.....',
                '...IBKKBEEEEEEC.....',
                '...IBKKBEEEELEC.....',
                '...IBBBBEEEEEEC.....',
                '...IBBBBICCCCC......',
                '...IBBBBICCC........',
                '...IBBBBLLLLC.......',
                '...IBBBBLLLLCC......',
                '...IBBBAAAAAAAC.....',
                '...CBBBAAAAAAAC.....',
                '...CBBBACFAAAAC.....',
                '...CBBBACFAAAAC.....',
                '...CBBBACFAAAAC.....',
                '....CCCACFAAAAC.....',
                '......CCCEECCCC.....',
                '......CCCEECCCC.....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CFFFFFFFFFC....',
                '.....CFFFFFFFFFC....',
                '......CCAAAACCC.....',
                '.......CAAAAC.......',
                '.......CAAAAC.......',
                '.......CGGGGGC......',
                '.......CGGGGGC......',
                '........CCCCC.......',
            ],
            sideWalkA: [
                '.....IBBKKKKBI......',
                '....IIBBKKKKBI......',
                '...IBBBBBBBBBEC.....',
                '...IBBBBEEEEEEC.....',
                '...IBBBBEEEEJEC.....',
                '...IBBBBBEEEJEEC....',
                '...IBKKBEEEEEEC.....',
                '...IBKKBEEEEEEC.....',
                '...IBKKBEEEEEEC.....',
                '...IBKKBEEEEEEC.....',
                '...IBKKBEEEELEC.....',
                '...IBBBBEEEEEEC.....',
                '...IBBBBICCCCC......',
                '...IBBBBICCC........',
                '...IBBBBLLLLC.......',
                '...IBBBBLLLLCC......',
                '...IBBBAAAAAAAC.....',
                '...IBBBAAAAAAAC.....',
                '...CBBBACFAAAAC.....',
                '...CBBBCFAAAAAC.....',
                '...CBBBCFAAAAAC.....',
                '...CBBCFAAAAAAC.....',
                '....CCCEECCCCCC.....',
                '....CCEECCCCCCC.....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CFFFFFFFFFC....',
                '.....CFFFFFFFFFC....',
                '......CCCAAACCC.....',
                '.......CFFAAAC......',
                '......CFFFCAAAC.....',
                '.....CGGGGCAAACC....',
                '.....CGGGGCCGGGGC...',
                '......CCCC.CGGGGC...',
                '............CCCC....',
            ],
            sideWalkB: [
                '.....IBBKKKKBI......',
                '....IIBBKKKKBI......',
                '...IBBBBBBBBBEC.....',
                '...IBBBBEEEEEEC.....',
                '...IBBBBEEEEJEC.....',
                '...IBBBBBEEEJEEC....',
                '...IBKKBEEEEEEC.....',
                '...IBKKBEEEEEEC.....',
                '...IBKKBEEEEEEC.....',
                '...IBKKBEEEEEEC.....',
                '...IBKKBEEEELEC.....',
                '...IBBBBEEEEEEC.....',
                '...IBBBBICCCCC......',
                '...IBBBBICCC........',
                '...IBBBBLLLLC.......',
                '...IBBBBLLLLCC......',
                '...IBBBAAAAAAAC.....',
                '...IBBBAAAAAAAC.....',
                '...CBBBACFAAAAC.....',
                '...CBBBAACFAAAC.....',
                '...CBBBAACFAAAC.....',
                '...CBBBAAACFAAC.....',
                '....CCCCCCCEECC.....',
                '......CCCCCCEEC.....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CAAAAAAAAAC....',
                '.....CFFFFFFFFFC....',
                '.....CFFFFFFFFFC....',
                '......CCCAAACCC.....',
                '.......CAAAFFC......',
                '......CAAACFFFC.....',
                '.....CGGGGCFFFCC....',
                '.....CGGGGCCGGGGC...',
                '......CCCC.CGGGGC...',
                '............CCCC....',
            ],
        },
        dume: {
            bracket: "(D.U.M.-E.)",
            palette: { "A": '#7552db', "B": '#540f94', "C": '#6330b7', "D": '#410f67', "E": '#fedcdb', "F": '#b47646', "G": '#2b0050', "H": '#8c4977', "I": '#cbaafd', "J": '#c28ace', "K": '#834645', "L": '#a2615e', "M": '#692a81', "N": '#ad839a', "O": '#f1cbe4', "P": '#965e89', "Q": '#a672bf', "R": '#d7a996', "S": '#b67464', "T": '#7a3861', "U": '#7740c4', "V": '#9976e5' },
            rows: [
                '...............GDDDDD.........',
                '.............GDHFFFFLDD.......',
                '............DHFFSSSSFFLD......',
                '...........DPFFSTDDHSSFLD.....',
                '...........DPSTBQEENDMFSD.....',
                '............DBJEEEEEEOBD......',
                '............DBJEEEEEEOBD......',
                '...........DIPJPBQENBDMOD.....',
                '...........DIPJEQQENUOMOD.....',
                '............DHREERSREEOD......',
                '............DHFRRKDHSELB......',
                '............DHFFKHFKTFLD......',
                '.............DHFFSFSSLD.......',
                '.............DBBBDDDBBD.......',
                '.DBBG.....DBBBCCQEENCABBBD....',
                'DOEEDG...DUAACCACBBCAABAAAD...',
                'DOEEUBG.DUAAACCACBBCAABAAAAD..',
                'DOEEUABBUAAAACBBCCCCBBBAAAAUD.',
                '.BBUAAAAAAAAAAAAACCAAAAAAAAAB.',
                '...DAAAAAACUAAAAACCVIIIIAAAAB.',
                '....DAAAABBUCBBBCCCCBBBMABAAUD',
                '.....BAABGDUCCACCCCCCAUBABAAAD',
                '......DBG.DUBUACCCCCCAUBABAAAD',
                '..........DUACBCACCAUBCAABAAAB',
                '..........DUAAAAACCAAAAAABAAAB',
                '..........DBBBBBBBBBBBBBBBAAAB',
                '..........DCAAACBBBBCAAACBAAAB',
                '..........DBBBBBBBBBBBBBBBAAAB',
                '..........DCUUAAAAAAAAAACMOOJD',
                '..........DUAAAAAAAAAAAAAMEEEB',
                '..........DUAAAAAAAAAAAAABMMM.',
                '..........DUAAAUBBBBUAAAABGGG.',
                '..........DUAAACDGGDCAAAAD....',
                '..........DUAAACD...CAAAAD....',
                '..........DUAAACD...CAAAAD....',
                '..........DUAAACD...CAAAAD....',
                '..........DUAAACD...CAAAAD....',
                '..........DBCCCBD...BCCCCD....',
                '..........BCCCCBD...BCCCCCG...',
                '.........DBCCCCBD...BUCCCCB...',
            ],
            up: [
                '......DDDDDDDD......',
                '.....DFFFFFFFFD.....',
                '.....DFLLLLLLFD.....',
                '....DFFLLLLLLFFD....',
                '....DFFFFFFFFFFD....',
                '...DEFFFFFFFFFFED...',
                '....DFFFFFFFFFFD....',
                '....DFFFFFFFFFFD....',
                '....DFFFFFFFFFFD....',
                '....DFFFFFFFFFFD....',
                '....DFFFFFFFFFFD....',
                '....DFFFFFFFFFFD....',
                '.....DDDEEEEDDD.....',
                '.......DEEEED.......',
                '....DDDDRRRRDDDD....',
                '..DDBBBBBBBBBBBBDD..',
                '.DBBBBBBBBBBBBBBBBD.',
                '.DBBAAAAAABAAAAABBD.',
                '.DBBAAAAAABAAAAABBD.',
                '.DBBAAAAAABAAAAABBD.',
                '.DBBAAAAAABAAAAABBD.',
                '.DBBAAAAAABAAAAABBD.',
                '.DBBAAAAAABAAAAABBD.',
                '.DBBAAAAAABAAAAABBD.',
                '.DBBAAAAAABAAAAABBD.',
                '.DBBAAAAAABAAAAABBD.',
                '.DEEDDDDDDDDDDDDEED.',
                '.DEEDDDDDDDDDDDDEED.',
                '..DDDDAAADDAAADDDD..',
                '.....DAAADDAAAD.....',
                '.....DAAADDAAAD.....',
                '.....DAAADDAAAD.....',
                '.....DAAADDAAAD.....',
                '.....DAAADDAAAD.....',
                '.....DAAADDAAAD.....',
                '.....DAAADDAAAD.....',
                '.....DAAADDAAAD.....',
                '.....DCCCDDCCCD.....',
                '.....DCCCDDCCCD.....',
                '......DDD..DDD......',
            ],
            sideIdle: [
                '.......DDDDDDD........',
                '......DFFLLLLFD.......',
                '......DFFLLLLFD.......',
                '.....DFFFFFFFFED......',
                '.....DFFFEEEEEED......',
                '.....DFFFEEEEDED......',
                '.....DFFFFEEEDEED.....',
                '.....DFFFEEEEEED......',
                '.....DFFFFFFFFFFD.....',
                '.....DFFFFFFFFFFD.....',
                '.....DFFFFFFFFFD......',
                '......DDEFFFFFFD......',
                '........DFFFFFFD......',
                '.........DDDDDD.......',
                '.......DDRRRRDDD......',
                '......DAAAAAAAAAD.....',
                '......DAAAAAAAAFD.....',
                '......DAADBAABBAD.....',
                '......DAADBAABBAD.....',
                '......DAADBAABBCD.....',
                '......DAADBAAAAAD.....',
                '......DAADBAAAAAD.....',
                '......DAADBAAAAAD.....',
                '......DAADBAAAAAD.....',
                '......DAADBAAAAAD.....',
                '......DAADBAAAAAD.....',
                '......DDDDEEDDDDD.....',
                '......DDDDEEDDDDD.....',
                '.......DDAAAADDD......',
                '........DAAAAD........',
                '........DAAAAD........',
                '........DAAAAD........',
                '........DAAAAD........',
                '........DAAAAD........',
                '........DAAAAD........',
                '........DAAAAD........',
                '........DAAAAD........',
                '........DCCCCCD.......',
                '........DCCCCCD.......',
                '.........DDDDD........',
            ],
            sideWalkA: [
                '......DFFLLLLFD.......',
                '......DFFLLLLFD.......',
                '.....DFFFFFFFFED......',
                '.....DFFFEEEEEED......',
                '.....DFFFEEEEDED......',
                '.....DFFFFEEEDEED.....',
                '.....DFFFEEEEEED......',
                '.....DFFFFFFFFFFD.....',
                '.....DFFFFFFFFFFD.....',
                '.....DFFFFFFFFFD......',
                '......DDEFFFFFFD......',
                '........DFFFFFFD......',
                '.........DDDDDD.......',
                '.......DDRRRRDDD......',
                '......DAAAAAAAAAD.....',
                '......DAAAAAAAAFD.....',
                '......DAADBAABBAD.....',
                '......DAADBAABBAD.....',
                '......DADBAAABBCD.....',
                '......DADBAAAAAAD.....',
                '......DADBAAAAAAD.....',
                '......DDBAAAAAAAD.....',
                '......DDBAAAAAAAD.....',
                '......DDBAAAAAAAD.....',
                '......DDBAAAAAAAD.....',
                '.....DDEEDDDDDDDD.....',
                '.....DDEEDDDDDDDD.....',
                '......DDDDAAADDD......',
                '.........DAAAD........',
                '........DBBAAAD.......',
                '........DBBAAAD.......',
                '........DBBAAAD.......',
                '.......DBBBDAAAD......',
                '.......DBBBDAAAD......',
                '.......DBBBDAAAD......',
                '.......DBBBDAAAD......',
                '......DCCCCDDAAAD.....',
                '......DCCCCDDCCCCD....',
                '.......DDDD.DCCCCD....',
                '.............DDDD.....',
            ],
            sideWalkB: [
                '......DFFLLLLFD.......',
                '......DFFLLLLFD.......',
                '.....DFFFFFFFFED......',
                '.....DFFFEEEEEED......',
                '.....DFFFEEEEDED......',
                '.....DFFFFEEEDEED.....',
                '.....DFFFEEEEEED......',
                '.....DFFFFFFFFFFD.....',
                '.....DFFFFFFFFFFD.....',
                '.....DFFFFFFFFFD......',
                '......DDEFFFFFFD......',
                '........DFFFFFFD......',
                '.........DDDDDD.......',
                '.......DDRRRRDDD......',
                '......DAAAAAAAAAD.....',
                '......DAAAAAAAAFD.....',
                '......DAADBAABBAD.....',
                '......DAADBAABBAD.....',
                '......DAAADBABBCD.....',
                '......DAAADBAAAAD.....',
                '......DAAADBAAAAD.....',
                '......DAAAADBAAAD.....',
                '......DAAAADBAAAD.....',
                '......DAAAADBAAAD.....',
                '......DAAAADBAAAD.....',
                '......DDDDDDDEEDD.....',
                '......DDDDDDDEEDD.....',
                '.......DDDAAADDD......',
                '.........DAAAD........',
                '........DAAABBD.......',
                '........DAAABBD.......',
                '........DAAABBD.......',
                '.......DAAADBBBD......',
                '.......DAAADBBBD......',
                '.......DAAADBBBD......',
                '.......DAAADBBBD......',
                '......DCCCCDDBBBD.....',
                '......DCCCCDDCCCCD....',
                '.......DDDD.DCCCCD....',
                '.............DDDD.....',
            ],
        },
        u: {
            bracket: "<U.>",
            palette: { "A": '#7a51d9', "B": '#540f92', "C": '#ffdbe6', "D": '#b47652', "E": '#2e0455', "F": '#4f1271', "G": '#682eba', "H": '#cbb0ff' },
            rows: [
                '.........FFFFFF..........',
                '.......FFDDDDDDF.........',
                '......FDDDDDDDDDF........',
                '......FDDDDDDDDDDF.......',
                '.....FDFDDFDDDDFDF.......',
                '.....BDDBFCFFFFCFB.......',
                '.....BDDFCCCCCCCBB.......',
                '.....BDDBCCCCCCCBB.......',
                '.....BDDBCBBFCFFB........',
                '......FFBCBFCCFCB........',
                '.FF...FCFCCCCCCCB.....FF.',
                'FCCF..FCCCFCCCCCB....FCCF',
                'FCCAF..FFCCFFFCCB...FACCF',
                'EFBAAB...FCCCCCF...FAABFE',
                '...BAAF...FBFBF...FAABE..',
                '....BAABBBABCBABBBAABE...',
                '.....BAAABAAFAABAAABE....',
                '......BBABBBBBBBABBE.....',
                '.......EBAAABAAABE.......',
                '........BHHABABBB........',
                '........BABABABAB........',
                '........BBAABAABB........',
                '........BAAABAAAB........',
                '........BBBBBBBBB........',
                '........BAABBBAAB........',
                '........BBBBBBBBB........',
                '........BAAAAAAAB........',
                '........BAAAAAAAB........',
                '........BAAAAAAAB........',
                '........BAABBBAAB........',
                '........BAABEBAAB........',
                '........BAAB.BAAB........',
                '........BAAB.BAAB........',
                '........BGBB.BGGB........',
                '.......EGGGB.BGGGE.......',
                '.......BGGGB.BGGGB.......',
                '.......FEEEE.EEEEE.......',
            ],
            up: [
                '......FFFFFFF.....',
                '.....FDDDDDDDF....',
                '.....FDDDDDDDF....',
                '....FDDDDDDDDDF...',
                '....FDDDDDDDDDF...',
                '...FCDDDDDDDDDCF..',
                '....FDDDDDDDDDF...',
                '....FDDDDDDDDDF...',
                '....FDDDDDDDDDF...',
                '....FDDDDDDDDDF...',
                '....FDDDDDDDDDF...',
                '.....FFCCCCFFF....',
                '......FCCCCF......',
                '......FHHHHF......',
                '.....FFHHHHFFF....',
                '...FFBBBBBBBBBFF..',
                '..FBBBBBBBBBBBBBF.',
                '..FBBAAAABAAAABBF.',
                '..FBBAAAABAAAABBF.',
                '..FBBAAAABAAAABBF.',
                '..FBBAAAABAAAABBF.',
                '..FBBAAAABAAAABBF.',
                '..FBBAAAABAAAABBF.',
                '..FBBAAAABAAAABBF.',
                '..FBBAAAABAAAABBF.',
                '..FCCFFFFFFFFFCCF.',
                '..FCCFFFFFFFFFCCF.',
                '...FFFAAFFAAFFFF..',
                '.....FAAFFAAF.....',
                '.....FAAFFAAF.....',
                '.....FAAFFAAF.....',
                '.....FAAFFAAF.....',
                '.....FAAFFAAF.....',
                '.....FAAFFAAF.....',
                '.....FGGFFGGF.....',
                '.....FGGFFGGF.....',
                '......FF..FF......',
            ],
            sideIdle: [
                '......FFFFFFF.......',
                '.....FDDDDDDDF......',
                '.....FDDDDDDDF......',
                '....FDDDDDDDDCF.....',
                '....FDDDCCCCCCF.....',
                '....FDDDCCCCECF.....',
                '....FDDDDCCCECCF....',
                '....FDDDCCCCCCF.....',
                '....FDDDCCCCCCF.....',
                '....FDDDCCCCHCF.....',
                '.....FFCCCCCCCF.....',
                '.......FFFFFFF......',
                '........FFFF........',
                '.......FHHHHF.......',
                '.......FHHHHFF......',
                '......FAAAAAAAF.....',
                '......FAAAAAAAF.....',
                '......FAFBAAAAF.....',
                '......FAFBAAAAF.....',
                '......FAFBAAAAF.....',
                '......FAFBAAAAF.....',
                '......FAFBAAAAF.....',
                '......FAFBAAAAF.....',
                '......FAFBAAAAF.....',
                '......FAFBAAAAF.....',
                '......FFFCCFFFF.....',
                '......FFFCCFFFF.....',
                '.......FAAAAFF......',
                '.......FAAAAF.......',
                '.......FAAAAF.......',
                '.......FAAAAF.......',
                '.......FAAAAF.......',
                '.......FAAAAF.......',
                '.......FAAAAF.......',
                '.......FGGGGGF......',
                '.......FGGGGGF......',
                '........FFFFF.......',
            ],
            sideWalkA: [
                '.....FDDDDDDDF......',
                '.....FDDDDDDDF......',
                '....FDDDDDDDDCF.....',
                '....FDDDCCCCCCF.....',
                '....FDDDCCCCECF.....',
                '....FDDDDCCCECCF....',
                '....FDDDCCCCCCF.....',
                '....FDDDCCCCCCF.....',
                '....FDDDCCCCHCF.....',
                '.....FFCCCCCCCF.....',
                '.......FFFFFFF......',
                '........FFFF........',
                '.......FHHHHF.......',
                '.......FHHHHFF......',
                '......FAAAAAAAF.....',
                '......FAAAAAAAF.....',
                '......FAFBAAAAF.....',
                '......FAFBAAAAF.....',
                '......FFBAAAAAF.....',
                '......FFBAAAAAF.....',
                '......FFBAAAAAF.....',
                '.....FFBAAAAAAF.....',
                '.....FFBAAAAAAF.....',
                '.....FFBAAAAAAF.....',
                '....FFCCFFFFFFF.....',
                '....FFCCFFFFFFF.....',
                '.....FFFFAAAFF......',
                '........FAAAF.......',
                '.......FBBAAAF......',
                '.......FBBAAAF......',
                '......FBBBFAAAF.....',
                '......FBBBFAAAF.....',
                '......FBBBFAAAF.....',
                '.....FGGGGFFAAAF....',
                '.....FGGGGFFGGGGF...',
                '......FFFF.FGGGGF...',
                '............FFFF....',
            ],
            sideWalkB: [
                '.....FDDDDDDDF......',
                '.....FDDDDDDDF......',
                '....FDDDDDDDDCF.....',
                '....FDDDCCCCCCF.....',
                '....FDDDCCCCECF.....',
                '....FDDDDCCCECCF....',
                '....FDDDCCCCCCF.....',
                '....FDDDCCCCCCF.....',
                '....FDDDCCCCHCF.....',
                '.....FFCCCCCCCF.....',
                '.......FFFFFFF......',
                '........FFFF........',
                '.......FHHHHF.......',
                '.......FHHHHFF......',
                '......FAAAAAAAF.....',
                '......FAAAAAAAF.....',
                '......FAFBAAAAF.....',
                '......FAFBAAAAF.....',
                '......FAAFBAAAF.....',
                '......FAAFBAAAF.....',
                '......FAAFBAAAF.....',
                '......FAAAFBAAF.....',
                '......FAAAFBAAF.....',
                '......FAAAFBAAF.....',
                '......FFFFFFCCF.....',
                '......FFFFFFCCF.....',
                '.......FFAAAFF......',
                '........FAAAF.......',
                '.......FAAABBF......',
                '.......FAAABBF......',
                '......FAAAFBBBF.....',
                '......FAAAFBBBF.....',
                '......FAAAFBBBF.....',
                '.....FGGGGFFBBBF....',
                '.....FGGGGFFGGGGF...',
                '......FFFF.FGGGGF...',
                '............FFFF....',
            ],
        },
        veronica: {
            bracket: "(V.E.R.O.N.I.C.A.)",
            palette: { "K": '#5c0b1e', "D": '#881337', "R": '#ef4444', "r": '#b91c1c', "G": '#f59e0b', "g": '#b45309', "Y": '#fde047', "C": '#38bdf8', "c": '#bae6fd', "S": '#ffdbe6', "s": '#dba0b0', "H": '#7c2d12', "h": '#ea580c', "W": '#ffffff', "P": '#3b071e', "p": '#6b1234' },
            rows: [
                '.......KKKKKKK.........',
                '.....KKHHHHHHHKK.......',
                '....KHHhhhhhhhHHK......',
                '....KHhHHHHHHHHhK......',
                '...KHHKSSSSSSSKHHK.....',
                '...KHKSKWKSSKWKSHK.....',
                '...KHKSSSKSSKSSSHK.....',
                '....KKSSSSSSSSSKK......',
                '....KKSSKKKKKSSKK......',
                '.....KSSSSSSSSSK.......',
                '......KKsKKKsKK........',
                '.....KKKRRRRRKKK.......',
                '...KKGGGGRRRGGGGKK.....',
                '..KGGGRRRCccCRRGGGK....',
                '.KGGDRRRRCCYCRRRDGGK...',
                '.KGRDKRRRRRRRRRKDRGK...',
                'KGRDK.KRRGGGGRK.KDRGK..',
                'KRrK..KRRRRRRRK..KRrK..',
                'KSSK..KRRRRRRRK..KSSK..',
                '.KK...KGGYYYGGK...KK...',
                '......KDDDDDDDK........',
                '......KRRRRRRRK........',
                '......KRRRRRRRK........',
                '......KRRKKKRRK........',
                '......KppK.KppK........',
                '......KppK.KppK........',
                '......KPPK.KPPK........',
                '......KppK.KppK........',
                '......KppK.KppK........',
                '......KPPK.KPPK........',
                '......KPPK.KPPK........',
                '......KppK.KppK........',
                '......KRRK.KRRK........',
                '.....KGGDK.KDGGK.......',
                '.....KGGDK.KDGGK.......',
                '.....KRRDK.KDRRK.......',
                '.....KDDDK.KDDDK.......',
                '.....KKKKK.KKKKK.......',
            ],
            up: [
                '......KKKKKKK.....',
                '.....KHHHHHHHK....',
                '.....KHhhhhhHK....',
                '....KHHhhhhhHHK...',
                '....KHHHHHHHHHK...',
                '...KSHHHHHHHHHSK..',
                '....KHHHHHHHHHK...',
                '....KHHHHHHHHHK...',
                '....KHHHHHHHHHK...',
                '.....KKSSSSKKK....',
                '......KSSSSK......',
                '....KKKssssKKK....',
                '..KKrrrrrrrrrrKK..',
                '.KrrrrrrrrrrrrrrK.',
                '.KrrRRRRRrRRRRrrK.',
                '.KrrRRRRRrRRRRrrK.',
                '.KrrRRRRRrRRRRrrK.',
                '.KrrRRRRRrRRRRrrK.',
                '.KrrRRRRRrRRRRrrK.',
                '.KrrRRRRRrRRRRrrK.',
                '.KrrRRRRRrRRRRrrK.',
                '.KrrRRRRRrRRRRrrK.',
                '.KSSGGGGGGGGGGSSK.',
                '.KSSGGGGGGGGGGSSK.',
                '..KKKKDDKKDDKKKK..',
                '.....KDDKKDDK.....',
                '.....KDDKKDDK.....',
                '.....KDDKKDDK.....',
                '.....KDDKKDDK.....',
                '.....KDDKKDDK.....',
                '.....KDDKKDDK.....',
                '.....KDDKKDDK.....',
                '.....KDDKKDDK.....',
                '.....KDDKKDDK.....',
                '.....KDDKKDDK.....',
                '.....KDDKKDDK.....',
                '.....KDDKKDDK.....',
                '......KK..KK......',
            ],
            sideIdle: [
                '......KKKKKKK.......',
                '.....KHHhhhhHK......',
                '.....KHHhhhhHK......',
                '....KHHHHHHHHSK.....',
                '....KHHHSSSSSSK.....',
                '....KHHHSSSSKSK.....',
                '....KHHHHSSSKSSK....',
                '....KHHHSSSSsSK.....',
                '.....KKSSSSSSSK.....',
                '.......KKKKKKK......',
                '........KKKK........',
                '.......KssssKK......',
                '......KRRRRRRRK.....',
                '......KRRRRRRRK.....',
                '......KRKrRRRRK.....',
                '......KRKrRRCCK.....',
                '......KRKrRRCCK.....',
                '......KRKrRRRRK.....',
                '......KRKrRRRRK.....',
                '......KRKrRRRRK.....',
                '......KRKrRRRRK.....',
                '......KRKrRRRRK.....',
                '......KGKSSGGGK.....',
                '......KGKSSGGGK.....',
                '.......KDDDDKK......',
                '.......KDDDDK.......',
                '.......KDDDDK.......',
                '.......KDDDDK.......',
                '.......KDDDDK.......',
                '.......KDDDDK.......',
                '.......KDDDDK.......',
                '.......KDDDDK.......',
                '.......KDDDDK.......',
                '.......KDDDDK.......',
                '.......KDDDDK.......',
                '.......KDDDDDK......',
                '.......KDDDDDK......',
                '........KKKKK.......',
            ],
            sideWalkA: [
                '.....KHHhhhhHK......',
                '.....KHHhhhhHK......',
                '....KHHHHHHHHSK.....',
                '....KHHHSSSSSSK.....',
                '....KHHHSSSSKSK.....',
                '....KHHHHSSSKSSK....',
                '....KHHHSSSSsSK.....',
                '.....KKSSSSSSSK.....',
                '.......KKKKKKK......',
                '........KKKK........',
                '.......KssssKK......',
                '......KRRRRRRRK.....',
                '......KRRRRRRRK.....',
                '......KRKrRRRRK.....',
                '......KRKrRRCCK.....',
                '......KKrRRRCCK.....',
                '......KKrRRRRRK.....',
                '......KKrRRRRRK.....',
                '.....KKrRRRRRRK.....',
                '.....KKrRRRRRRK.....',
                '.....KKrRRRRRRK.....',
                '....KKSSGGGGGGK.....',
                '....KKSSGGGGGGK.....',
                '.....KKKKDDDKK......',
                '........KDDDK.......',
                '........KDDDK.......',
                '.......KrrDDDK......',
                '.......KrrDDDK......',
                '.......KrrDDDK......',
                '......KrrrKDDDK.....',
                '......KrrrKDDDK.....',
                '......KrrrKDDDK.....',
                '......KrrrKDDDK.....',
                '......KrrrKDDDK.....',
                '.....KDDDDKKDDDK....',
                '.....KDDDDKKDDDDK...',
                '......KKKK.KDDDDK...',
                '............KKKK....',
            ],
            sideWalkB: [
                '.....KHHhhhhHK......',
                '.....KHHhhhhHK......',
                '....KHHHHHHHHSK.....',
                '....KHHHSSSSSSK.....',
                '....KHHHSSSSKSK.....',
                '....KHHHHSSSKSSK....',
                '....KHHHSSSSsSK.....',
                '.....KKSSSSSSSK.....',
                '.......KKKKKKK......',
                '........KKKK........',
                '.......KssssKK......',
                '......KRRRRRRRK.....',
                '......KRRRRRRRK.....',
                '......KRKrRRRRK.....',
                '......KRKrRRCCK.....',
                '......KRRKrRCCK.....',
                '......KRRKrRRRK.....',
                '......KRRKrRRRK.....',
                '......KRRRKrRRK.....',
                '......KRRRKrRRK.....',
                '......KRRRKrRRK.....',
                '......KGGGGKSSK.....',
                '......KGGGGKSSK.....',
                '.......KKDDDKK......',
                '........KDDDK.......',
                '........KDDDK.......',
                '.......KDDDrrK......',
                '.......KDDDrrK......',
                '.......KDDDrrK......',
                '......KDDDKrrrK.....',
                '......KDDDKrrrK.....',
                '......KDDDKrrrK.....',
                '......KDDDKrrrK.....',
                '......KDDDKrrrK.....',
                '.....KDDDDKKrrrK....',
                '.....KDDDDKKDDDDK...',
                '......KKKK.KDDDDK...',
                '............KKKK....',
            ],
        },
        jocasta: {
            bracket: "<J.O.C.A.S.T.A.>",
            palette: { "K": '#0f4c75', "D": '#16658a', "C": '#06b6d4', "c": '#a5f3fc', "L": '#cbd5e1', "l": '#94a3b8', "W": '#f8fafc', "S": '#ffe4e8', "s": '#d4b0bc', "H": '#e2e8f0', "h": '#64748b', "P": '#1e3a5f' },
            rows: [
                '.......KKKKKKK.......',
                '.....KKWWWWWWWKK.....',
                '....KWWLLLLLLLWWK....',
                '....KWLhhHHHHhLWK....',
                '...KWLHSSSSSSSSHWK...',
                '...KWLHSKKSSKKSHWK...',
                '...KWLHSWCSSWCSHWK...',
                '...KWLHSSSSSSSSSHK...',
                '...KWLhhSSKKKKSSKK...',
                '....KKh.KSSSSSSK.....',
                '........KKsKKsKK.....',
                '.......KLLLLLLLK.....',
                '.....KKWWLLCCCLWWKK..',
                '....KWWLLLCCCCLLLWWK.',
                '...KWLKDKLLLLLLKDKLWK',
                '..KCCCK.KLLWWLLK.KLLK',
                '..KCCSK.KLWWWWLK.KLLK',
                '..KSSK..KLLWWLLK.KSSK',
                '...KK...KLLLLLLK..KK.',
                '.......KLLCCCCLLK....',
                '.......KLLLLLLLLK....',
                '.......KLLWWWWLLK....',
                '.......KLLLLLLLLK....',
                '.......KLLLLLLLLK....',
                '.......KllK..KllK....',
                '.......KllK..KllK....',
                '.......KLLK..KLLK....',
                '.......KPPK..KPPK....',
                '.......KPPK..KPPK....',
                '.......KPPK..KPPK....',
                '.......KPPK..KPPK....',
                '.......KPPK..KPPK....',
                '.......KPPK..KPPK....',
                '.......KDDK..KDDK....',
                '......KCCDK..KDCCK...',
                '......KDDDK..KDDDK...',
                '......KKKKK..KKKKK...',
            ],
            up: [
                '......KKKKKKK.....',
                '.....KHHHHHHHK....',
                '.....KHlllllHK....',
                '....KHHHHHHHHHK...',
                '....KHHHHHHHHHK...',
                '...KSHHHHHHHHHSK..',
                '....KHHHHHHHHHK...',
                '....KHHHHHHHHHK...',
                '....KHlllllllHK...',
                '....KHlllllllHK...',
                '....KHHHHHHHHHK...',
                '.....KKssssKKK....',
                '...KKlllllllllKK..',
                '..KlllllllllllllK.',
                '..KllLLLLlLLLLllK.',
                '..KllLLLLlLLLLllK.',
                '..KllLLLLlLLLLllK.',
                '..KllLLLLlLLLLllK.',
                '..KllLLLLlLLLLllK.',
                '..KllLLLLlLLLLllK.',
                '..KllLLLLlLLLLllK.',
                '..KllLLLLlLLLLllK.',
                '..KllLLLLlLLLLllK.',
                '..KSSCCCCCCCCCSSK.',
                '..KSSCCCCCCCCCSSK.',
                '...KKKKKKKKKKKKK..',
                '......KK..KK......',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '......KK..KK......',
            ],
            sideIdle: [
                '......KKKKKKK.......',
                '.....KHHllllHK......',
                '.....KHHllllHK......',
                '....KHHHHHHHHSK.....',
                '....KHHHHSSSSSK.....',
                '....KHHHHSSCCSK.....',
                '....KHHHHSSSCSSK....',
                '....KHHHHSSSsSK.....',
                '....KHHHHSSSSSK.....',
                '....KHHHHKKKKK......',
                '....KHHHHKKK........',
                '.....KKKssssKK......',
                '......KLLLLLLLK.....',
                '......KLLLLLLLK.....',
                '......KLKlLLLLK.....',
                '......KLKlLLLLK.....',
                '......KLKlLLLLK.....',
                '......KLKlLLLLK.....',
                '......KLKlLLLLK.....',
                '......KLKlLLLLK.....',
                '......KLKlLLLLK.....',
                '......KLKlLLLLK.....',
                '......KLKlLLLLK.....',
                '......KCKSSCCCK.....',
                '......KCKSSCCCK.....',
                '.......KKKKKKK......',
                '........KKKK........',
                '.......KPPPPK.......',
                '.......KPPPPK.......',
                '.......KPPPPK.......',
                '.......KPPPPK.......',
                '.......KPPPPK.......',
                '.......KPPPPK.......',
                '.......KPPPPK.......',
                '.......KPPPPPK......',
                '.......KPPPPPK......',
                '........KKKKK.......',
            ],
            sideWalkA: [
                '.....KHHllllHK......',
                '.....KHHllllHK......',
                '....KHHHHHHHHSK.....',
                '....KHHHHSSSSSK.....',
                '....KHHHHSSCCSK.....',
                '....KHHHHSSSCSSK....',
                '....KHHHHSSSsSK.....',
                '....KHHHHSSSSSK.....',
                '....KHHHHKKKKK......',
                '....KHHHHKKK........',
                '.....KKKssssKK......',
                '......KLLLLLLLK.....',
                '......KLLLLLLLK.....',
                '......KLKlLLLLK.....',
                '......KLKlLLLLK.....',
                '......KKlLLLLLK.....',
                '......KKlLLLLLK.....',
                '......KKlLLLLLK.....',
                '.....KKlLLLLLLK.....',
                '.....KKlLLLLLLK.....',
                '.....KKlLLLLLLK.....',
                '.....KKlLLLLLLK.....',
                '....KKSSCCCCCCK.....',
                '....KKSSCCCCCCK.....',
                '.....KKKKKKKKK......',
                '.........KKK........',
                '........KPPPK.......',
                '........KPPPK.......',
                '.......KllPPPK......',
                '.......KllPPPK......',
                '......KlllKPPPK.....',
                '......KlllKPPPK.....',
                '......KlllKPPPK.....',
                '.....KPPPPKKPPPK....',
                '.....KPPPPKKPPPPK...',
                '......KKKK.KPPPPK...',
                '............KKKK....',
            ],
            sideWalkB: [
                '.....KHHllllHK......',
                '.....KHHllllHK......',
                '....KHHHHHHHHSK.....',
                '....KHHHHSSSSSK.....',
                '....KHHHHSSCCSK.....',
                '....KHHHHSSSCSSK....',
                '....KHHHHSSSsSK.....',
                '....KHHHHSSSSSK.....',
                '....KHHHHKKKKK......',
                '....KHHHHKKK........',
                '.....KKKssssKK......',
                '......KLLLLLLLK.....',
                '......KLLLLLLLK.....',
                '......KLKlLLLLK.....',
                '......KLKlLLLLK.....',
                '......KLLKlLLLK.....',
                '......KLLKlLLLK.....',
                '......KLLKlLLLK.....',
                '......KLLLKlLLK.....',
                '......KLLLKlLLK.....',
                '......KLLLKlLLK.....',
                '......KLLLKlLLK.....',
                '......KCCCCKSSK.....',
                '......KCCCCKSSK.....',
                '.......KKKKKKK......',
                '.........KKK........',
                '........KPPPK.......',
                '........KPPPK.......',
                '.......KPPPllK......',
                '.......KPPPllK......',
                '......KPPPKlllK.....',
                '......KPPPKlllK.....',
                '......KPPPKlllK.....',
                '.....KPPPPKKlllK....',
                '.....KPPPPKKPPPPK...',
                '......KKKK.KPPPPK...',
                '............KKKK....',
            ],
        },
        karen: {
            bracket: "//K.A.R.E.N.//",
            palette: { "K": '#064e3b', "D": '#047857', "E": '#10b981', "e": '#059669', "M": '#6ee7b7', "T": '#2dd4bf', "C": '#ccfbf1', "H": '#854d0e', "h": '#ca8a04', "S": '#ffdbe6', "s": '#d89aa8', "P": '#0f3d4c', "p": '#155e75', "W": '#ffffff' },
            rows: [
                '...KKKK..............',
                '..KHHHHK..KKKKK......',
                '..KHHHKKKHHHHHHHK....',
                '..KHHKKKHHhhhhhHHK...',
                '...KKKHHHhhhhhhhHK...',
                '....KHHhHHHHHHHHHK...',
                '...KTTHHSSSSSSSSHK...',
                '...KTTKSSKWKSKWKHK...',
                '...KTCKSSKHKSKHKHK...',
                '....KKSSSSSSSSSSHK...',
                '.....KHHSSKKKSSKK....',
                '.....KHHKSSSSSSK.....',
                '......KK.KKsKKSKK....',
                '.....KKKKEEEEEKKKK...',
                '...KKEEMEEEEEEEEMKK..',
                '..KEEEMEEWWWWWEEMEK..',
                '..KEEEeEEEMWMEEeEEK..',
                '..KEEeKEEEEEEEEKEeEK.',
                '.KCCCCKKEEEEEEKEeEEK.',
                '.KCTTTK.KEEEEEKKEEEK.',
                '.KSSKK..KTTCCCK.KSSK.',
                '..KK....KEEEEEK..KK..',
                '........KEeEEeK......',
                '........KEEEEEK......',
                '........KEeKKeK......',
                '........KppKKppK.....',
                '........KppK.KppK....',
                '........KPPK.KPPK....',
                '........KppK.KppK....',
                '........KPPK.KPPK....',
                '........KPPK.KPPK....',
                '........KppK.KppK....',
                '........KPPK.KPPK....',
                '.......KTeDK.KDeTK...',
                '.......KTTDK.KDTTK...',
                '.......KPPDK.KDPPK...',
                '.......KKKKK.KKKKK...',
            ],
            up: [
                '......KKKKKKK.....',
                '.....KHHHHHHHK....',
                '.....KHhhhhhHK....',
                '....KHHhhhhhHHK...',
                '....KHHHHHHHHHK...',
                '...KSTHHHHHHHHSK..',
                '....KTHhhhhHHHK...',
                '....KTHhhhhHHHK...',
                '....KHHhhhhHHHK...',
                '....KHHhhhhHHHK...',
                '.....KKhhhhKKK....',
                '.......KKKK.......',
                '.....KKssssKKK....',
                '...KKeeeeeeeeeKK..',
                '..KeeeeeeeeeeeeeK.',
                '..KeeEEEEeEEEEeeK.',
                '..KeeEEEEeEEEEeeK.',
                '..KeeEEEEeEEEEeeK.',
                '..KeeEEEEeEEEEeeK.',
                '..KeeEEEEeEEEEeeK.',
                '..KeeEEEEeEEEEeeK.',
                '..KeeEEEEeEEEEeeK.',
                '..KeeEEEEeEEEEeeK.',
                '..KeeEEEEeEEEEeeK.',
                '..KSSTTTTTTTTTSSK.',
                '..KSSTTTTTTTTTSSK.',
                '...KKKPPKKPPKKKK..',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '.....KPPKKPPK.....',
                '......KK..KK......',
            ],
            sideIdle: [
                '......KKKKKKK.......',
                '.....KHHhhhhHK......',
                '...KKKHHhhhhHK......',
                '..KHHHHHHHHHHSK.....',
                '..KHHHHHSSSSSSK.....',
                '..KHHHHHTTSSKSK.....',
                '..KHHHHHTTSSKSSK....',
                '..KHHHHHTTSSSSK.....',
                '..KHHHHHSSSSsSK.....',
                '...KKKKSSSSSSSK.....',
                '.......KKKKKKK......',
                '........KKKK........',
                '.......KssssKK......',
                '......KEEEEEEEK.....',
                '......KEEEEEEEK.....',
                '......KEKeEEEEK.....',
                '......KEKeEEEEK.....',
                '......KEKeEEEEK.....',
                '......KEKeEEEEK.....',
                '......KEKeEEEEK.....',
                '......KEKeEEEEK.....',
                '......KEKeEEEEK.....',
                '......KEKeEEEEK.....',
                '......KEKeEEEEK.....',
                '......KTKSSTTTK.....',
                '......KTKSSTTTK.....',
                '.......KPPPPKK......',
                '.......KPPPPK.......',
                '.......KPPPPK.......',
                '.......KPPPPK.......',
                '.......KPPPPK.......',
                '.......KPPPPK.......',
                '.......KPPPPK.......',
                '.......KPPPPK.......',
                '.......KPPPPPK......',
                '.......KPPPPPK......',
                '........KKKKK.......',
            ],
            sideWalkA: [
                '.....KHHhhhhHK......',
                '...KKKHHhhhhHK......',
                '..KHHHHHHHHHHSK.....',
                '..KHHHHHSSSSSSK.....',
                '..KHHHHHTTSSKSK.....',
                '..KHHHHHTTSSKSSK....',
                '..KHHHHHTTSSSSK.....',
                '..KHHHHHSSSSsSK.....',
                '...KKKKSSSSSSSK.....',
                '.......KKKKKKK......',
                '........KKKK........',
                '.......KssssKK......',
                '......KEEEEEEEK.....',
                '......KEEEEEEEK.....',
                '......KEKeEEEEK.....',
                '......KEKeEEEEK.....',
                '......KKeEEEEEK.....',
                '......KKeEEEEEK.....',
                '......KKeEEEEEK.....',
                '.....KKeEEEEEEK.....',
                '.....KKeEEEEEEK.....',
                '.....KKeEEEEEEK.....',
                '.....KKeEEEEEEK.....',
                '....KKSSTTTTTTK.....',
                '....KKSSTTTTTTK.....',
                '.....KKKKPPPKK......',
                '........KPPPK.......',
                '.......KeePPPK......',
                '.......KeePPPK......',
                '.......KeePPPK......',
                '......KeeeKPPPK.....',
                '......KeeeKPPPK.....',
                '......KeeeKPPPK.....',
                '.....KPPPPKKPPPK....',
                '.....KPPPPKKPPPPK...',
                '......KKKK.KPPPPK...',
                '............KKKK....',
            ],
            sideWalkB: [
                '.....KHHhhhhHK......',
                '...KKKHHhhhhHK......',
                '..KHHHHHHHHHHSK.....',
                '..KHHHHHSSSSSSK.....',
                '..KHHHHHTTSSKSK.....',
                '..KHHHHHTTSSKSSK....',
                '..KHHHHHTTSSSSK.....',
                '..KHHHHHSSSSsSK.....',
                '...KKKKSSSSSSSK.....',
                '.......KKKKKKK......',
                '........KKKK........',
                '.......KssssKK......',
                '......KEEEEEEEK.....',
                '......KEEEEEEEK.....',
                '......KEKeEEEEK.....',
                '......KEKeEEEEK.....',
                '......KEEKeEEEK.....',
                '......KEEKeEEEK.....',
                '......KEEKeEEEK.....',
                '......KEEEKeEEK.....',
                '......KEEEKeEEK.....',
                '......KEEEKeEEK.....',
                '......KEEEKeEEK.....',
                '......KTTTTKSSK.....',
                '......KTTTTKSSK.....',
                '.......KKPPPKK......',
                '........KPPPK.......',
                '.......KPPPeeK......',
                '.......KPPPeeK......',
                '.......KPPPeeK......',
                '......KPPPKeeeK.....',
                '......KPPPKeeeK.....',
                '......KPPPKeeeK.....',
                '.....KPPPPKKeeeK....',
                '.....KPPPPKKPPPPK...',
                '......KKKK.KPPPPK...',
                '............KKKK....',
            ],
        },
    };

    const state = {
        isOpen: false,
        rafId: null,
        pollTimer: null,
        selectedAgent: 'friday',
        activeTab: 'tasks',     // 'tasks' | 'feed'
        composeMode: 'command', // 'command' | 'mission'
        handoffAgent: '',
        quorum: ['friday', 'veronica', 'edith', 'u'],
        snapshot: null,
        sprites: {},            // local interpolated canvas positions per agent_id
        frame: 0,
    };

    function escapeHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function authHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        if (window.JARVIS_TOKEN) {
            headers['X-Jarvis-Security-Token'] = window.JARVIS_TOKEN;
        }
        return headers;
    }

    function formatAgo(ts) {
        if (!ts) return '';
        const diff = Math.max(0, Math.floor(Date.now() / 1000 - ts));
        if (diff < 5) return 'just now';
        if (diff < 60) return `${diff}s ago`;
        const m = Math.floor(diff / 60);
        return `${m}m ago`;
    }

    // ── Public Toggle / Window Lifecycle ────────────────────────────────────
    window.toggleAgentOffice = function toggleAgentOffice() {
        if (state.isOpen) {
            window.closeAgentOfficeWindow();
        } else {
            window.openAgentOfficeWindow();
        }
    };

    window.openAgentOfficeWindow = function openAgentOfficeWindow() {
        if (document.getElementById('ai-office-overlay')) return;
        state.isOpen = true;
        updateToggleBtn(true, state.snapshot && state.snapshot.summary ? state.snapshot.summary.busy_agents : 0);
        buildModalDOM();
        fetchOfficeState();
        state.pollTimer = setInterval(fetchOfficeState, POLL_MS);
        startCanvasLoop();
    };

    window.closeAgentOfficeWindow = function closeAgentOfficeWindow() {
        state.isOpen = false;
        updateToggleBtn(false, state.snapshot && state.snapshot.summary ? state.snapshot.summary.busy_agents : 0);
        if (state.pollTimer) {
            clearInterval(state.pollTimer);
            state.pollTimer = null;
        }
        if (state.rafId) {
            cancelAnimationFrame(state.rafId);
            state.rafId = null;
        }
        const el = document.getElementById('ai-office-overlay');
        if (el) el.remove();
    };

    function updateToggleBtn(active, busyCount) {
        const btn = document.getElementById('office-toggle');
        if (!btn) return;
        const busy = Number(busyCount || 0);
        if (active) {
            btn.innerText = busy > 0 ? `AGENT OFFICE · ${busy} LIVE` : 'AGENT OFFICE: ON';
            btn.style.background = 'rgba(0, 210, 255, 0.18)';
            btn.style.borderColor = '#00d2ff';
            btn.style.color = '#00d2ff';
        } else if (busy > 0) {
            btn.innerText = `AGENT OFFICE · ${busy} ACTIVE`;
            btn.style.background = 'rgba(0, 210, 255, 0.14)';
            btn.style.borderColor = '#22d3ee';
            btn.style.color = '#67e8f9';
        } else {
            btn.innerText = 'AGENT OFFICE';
            btn.style.background = '';
            btn.style.borderColor = '';
            btn.style.color = '';
        }
    }

    // ── Modal DOM Scaffold ──────────────────────────────────────────────────
    function buildModalDOM() {
        const overlay = document.createElement('div');
        overlay.id = 'ai-office-overlay';
        overlay.className = 'ai-office-overlay';
        overlay.onclick = (e) => {
            if (e.target === overlay) window.closeAgentOfficeWindow();
        };

        overlay.innerHTML = `
            <div class="ai-office-shell" role="dialog" aria-label="Nachapol AI Office">
                <header class="ai-office-header">
                    <div class="ai-office-brand">
                        <span class="ai-office-live-dot"></span>
                        <div>
                            <div class="ai-office-title">NACHAPOL // AI OFFICE</div>
                            <div class="ai-office-subtitle">INSIDE THE VISION · MINDSPACE STUDIO</div>
                        </div>
                    </div>
                    <div class="ai-office-metrics" id="office-metrics-strip">
                        <span class="office-metric-pill">ACTIVE: <strong id="m-busy">0</strong>/8</span>
                        <span class="office-metric-pill">RUNNING: <strong id="m-running">0</strong></span>
                        <span class="office-metric-pill">DONE: <strong id="m-done">0</strong></span>
                    </div>
                    <div class="ai-office-header-actions">
                        <button class="office-btn-ghost" id="office-reset-btn" type="button">RESET HOUSE</button>
                        <button class="office-btn-ghost danger" id="office-close-btn" type="button">CLOSE [ESC]</button>
                    </div>
                </header>

                <div class="ai-office-grid">
                    <!-- Left 2/3: 2D Pixel Art Mindspace Manor Canvas -->
                    <section class="office-stage-card">
                        <div class="office-stage-bar">
                            <span style="font-family: var(--office-font-mono); color: var(--office-text-primary); font-weight: 600;">THE MINDSPACE // SHARED NEURAL STUDIO</span>
                            <div class="office-zone-legend">
                                <span>● LABS = TASK ROUTED</span>
                                <span>◆ SOFA = BRIEFING</span>
                                <span>○ ATRIUM = FREE ROAM</span>
                            </div>
                        </div>
                        <div class="office-canvas-wrap">
                            <canvas id="ai-office-canvas" width="${OFFICE_W}" height="${OFFICE_H}"></canvas>
                        </div>
                        <div class="office-inspector-bar" id="office-inspector">
                            <div class="office-inspector-left">
                                <span class="office-inspector-dot" id="insp-dot" style="background:#00c8ff;"></span>
                                <span class="office-inspector-name" id="insp-name">F.R.I.D.A.Y.</span>
                                <span class="office-inspector-task" id="insp-task">Click any agent in the lab or roster to direct-command.</span>
                            </div>
                            <span class="office-state-badge" id="insp-state">IDLE</span>
                        </div>
                    </section>

                    <!-- Right 1/3: Bento Ops Deck -->
                    <aside class="office-ops-card">
                        <div class="office-roster-grid" id="office-roster-grid"></div>

                        <div class="office-tabs-row">
                            <div class="office-tab-group">
                                <button class="office-tab-btn active" data-tab="tasks" type="button">TASK BOARD</button>
                                <button class="office-tab-btn" data-tab="feed" type="button">AGENT COMMS</button>
                            </div>
                            <span style="font-family: var(--office-font-mono); font-size: 0.64rem; color: var(--office-text-muted);" id="office-sync-label">SYNCING...</span>
                        </div>

                        <div class="office-scroll-body" id="office-ops-scroll">
                            <div class="office-empty-hint">Connecting to AI Office telemetry...</div>
                        </div>

                        <form class="office-composer" id="office-composer-form">
                            <div class="office-mode-row">
                                <div class="office-mode-pills">
                                    <button class="office-mode-pill active" data-mode="command" type="button">DIRECT @AGENT</button>
                                    <button class="office-mode-pill" data-mode="mission" type="button">MEETING MISSION</button>
                                </div>
                                <select id="office-handoff-select" class="office-select-inline" title="Optional handoff target">
                                    <option value="">No handoff</option>
                                    <option value="friday">→ @friday</option>
                                    <option value="veronica">→ @veronica</option>
                                    <option value="edith">→ @edith</option>
                                    <option value="u">→ @u</option>
                                    <option value="dume">→ @dume</option>
                                    <option value="jocasta">→ @jocasta</option>
                                    <option value="karen">→ @karen</option>
                                    <option value="jarvis">→ @jarvis</option>
                                </select>
                            </div>

                            <div class="office-quorum-bar" id="office-quorum-bar" style="display:none;"></div>

                            <div class="office-input-row">
                                <input class="office-input" id="office-prompt-input" type="text"
                                    placeholder="สั่งงานตรงถึง @friday หรือพิมพ์ @from -> @to ..." autocomplete="off">
                                <button class="office-btn-primary" id="office-submit-btn" type="submit">SEND</button>
                            </div>
                        </form>
                    </aside>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);

        // Bind header actions
        document.getElementById('office-close-btn').onclick = window.closeAgentOfficeWindow;
        document.getElementById('office-reset-btn').onclick = resetOfficeState;

        // Bind canvas click selection
        document.getElementById('ai-office-canvas').addEventListener('click', handleCanvasClick);

        // Bind tabs
        overlay.querySelectorAll('.office-tab-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                state.activeTab = btn.dataset.tab;
                overlay.querySelectorAll('.office-tab-btn').forEach((b) => b.classList.toggle('active', b === btn));
                renderOpsPanel();
            });
        });

        // Bind compose mode pills
        overlay.querySelectorAll('.office-mode-pill').forEach((btn) => {
            btn.addEventListener('click', () => {
                state.composeMode = btn.dataset.mode;
                overlay.querySelectorAll('.office-mode-pill').forEach((b) => b.classList.toggle('active', b === btn));
                updateComposerModeUI();
            });
        });

        // Bind handoff selector
        document.getElementById('office-handoff-select').addEventListener('change', (e) => {
            state.handoffAgent = e.target.value;
        });

        // Bind form submit
        document.getElementById('office-composer-form').addEventListener('submit', handleComposerSubmit);

        // Escape key handler while modal open
        document.addEventListener('keydown', handleKeydown);
    }

    function handleKeydown(e) {
        if (e.key === 'Escape' && state.isOpen) {
            window.closeAgentOfficeWindow();
        }
        if (!state.isOpen) {
            document.removeEventListener('keydown', handleKeydown);
        }
    }

    function updateComposerModeUI() {
        const input = document.getElementById('office-prompt-input');
        const submitBtn = document.getElementById('office-submit-btn');
        const handoffSel = document.getElementById('office-handoff-select');
        const quorumBar = document.getElementById('office-quorum-bar');
        if (!input || !submitBtn) return;

        if (state.composeMode === 'mission') {
            handoffSel.style.display = 'none';
            quorumBar.style.display = 'flex';
            input.placeholder = 'ป้อนภารกิจใหญ่เพื่อเรียกประชุมทีมที่ห้อง Meeting...';
            submitBtn.innerText = 'CONVENE TEAM';
            renderQuorumCheckboxes();
        } else {
            handoffSel.style.display = 'inline-block';
            quorumBar.style.display = 'none';
            input.placeholder = `สั่งงานตรงถึง @${state.selectedAgent} (เช่น วิเคราะห์โค้ด...)`;
            submitBtn.innerText = 'SEND';
        }
    }

    function renderQuorumCheckboxes() {
        const bar = document.getElementById('office-quorum-bar');
        if (!bar || !state.snapshot) return;
        const specialists = state.snapshot.agents.filter((a) => a.agent_id !== 'jarvis');
        bar.innerHTML = specialists.map((a) => {
            const checked = state.quorum.includes(a.agent_id) ? 'checked' : '';
            return `
                <label class="office-quorum-check">
                    <input type="checkbox" value="${escapeHtml(a.agent_id)}" ${checked}>
                    <span style="color:${escapeHtml(a.color)};">●</span>
                    <span>@${escapeHtml(a.agent_id)}</span>
                </label>
            `;
        }).join('');

        bar.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
            cb.addEventListener('change', () => {
                const chosen = Array.from(bar.querySelectorAll('input:checked')).map((el) => el.value);
                state.quorum = chosen.length ? chosen : ['friday'];
            });
        });
    }

    // ── Backend API Calls ───────────────────────────────────────────────────
    async function fetchOfficeState() {
        try {
            const res = await fetch('/api/office/state', { headers: authHeaders() });
            if (!res.ok) return;
            const data = await res.json();
            state.snapshot = data;
            const busy = (data.summary && data.summary.busy_agents) || 0;
            updateToggleBtn(state.isOpen, busy);
            if (!state.isOpen) return;
            syncLocalSprites(data.agents || []);
            renderHeaderMetrics(data.summary || {});
            renderRoster(data.agents || []);
            renderInspector();
            renderOpsPanel();
            const lbl = document.getElementById('office-sync-label');
            if (lbl) lbl.innerText = 'LIVE SYNC · JARVIS CORE';
        } catch (err) {
            const lbl = document.getElementById('office-sync-label');
            if (lbl) lbl.innerText = 'RECONNECTING...';
        }
    }

    // Background HUD presence sync even when the Agent Office modal is minimized
    if (typeof window !== 'undefined') {
        setInterval(() => {
            if (!state.isOpen && !document.hidden) {
                fetchOfficeState();
            }
        }, 2500);
    }

    async function handleComposerSubmit(e) {
        e.preventDefault();
        const input = document.getElementById('office-prompt-input');
        const submitBtn = document.getElementById('office-submit-btn');
        if (!input || !input.value.trim()) return;

        const text = input.value.trim();
        input.value = '';
        if (submitBtn) submitBtn.disabled = true;

        try {
            if (state.composeMode === 'mission') {
                await fetch('/api/office/mission', {
                    method: 'POST',
                    headers: authHeaders(),
                    body: JSON.stringify({
                        mission: text,
                        agents: state.quorum,
                        async: true,
                    }),
                });
            } else {
                await fetch('/api/office/command', {
                    method: 'POST',
                    headers: authHeaders(),
                    body: JSON.stringify({
                        agent_id: state.selectedAgent,
                        prompt: text,
                        handoff_to: state.handoffAgent || null,
                        async: true,
                    }),
                });
            }
            await fetchOfficeState();
        } finally {
            if (submitBtn) submitBtn.disabled = false;
            input.focus();
        }
    }

    async function resetOfficeState() {
        await fetch('/api/office/reset', {
            method: 'POST',
            headers: authHeaders(),
        });
        await fetchOfficeState();
    }

    // ── UI Rendering (Roster, Inspector, Task Board, Agent Feed) ────────────
    function renderHeaderMetrics(summary) {
        const busyEl = document.getElementById('m-busy');
        const runEl = document.getElementById('m-running');
        const doneEl = document.getElementById('m-done');
        if (busyEl) busyEl.innerText = summary.busy_agents ?? 0;
        if (runEl) runEl.innerText = summary.in_progress_tasks ?? 0;
        if (doneEl) doneEl.innerText = summary.done_tasks ?? 0;
    }

    function renderRoster(agents) {
        const grid = document.getElementById('office-roster-grid');
        if (!grid) return;
        grid.innerHTML = agents.map((a) => {
            const isSel = a.agent_id === state.selectedAgent;
            const isActive = a.state !== 'IDLE';
            return `
                <button class="office-roster-chip ${isSel ? 'selected' : ''}" data-agent="${escapeHtml(a.agent_id)}" type="button" title="${escapeHtml(a.title)}">
                    <span class="office-chip-left">
                        <span class="office-chip-color" style="background:${escapeHtml(a.color)};"></span>
                        <span class="office-chip-name">${escapeHtml(a.name)}</span>
                    </span>
                    <span class="office-chip-state ${isActive ? 'active' : ''}">${escapeHtml(a.state)}</span>
                </button>
            `;
        }).join('');

        grid.querySelectorAll('.office-roster-chip').forEach((chip) => {
            chip.addEventListener('click', () => {
                selectAgent(chip.dataset.agent);
            });
        });
    }

    function selectAgent(agentId) {
        state.selectedAgent = agentId;
        if (state.snapshot) {
            renderRoster(state.snapshot.agents || []);
            renderInspector();
        }
        updateComposerModeUI();
        const input = document.getElementById('office-prompt-input');
        if (input && state.composeMode === 'command') input.focus();
    }

    function renderInspector() {
        if (!state.snapshot) return;
        const agent = (state.snapshot.agents || []).find((a) => a.agent_id === state.selectedAgent);
        if (!agent) return;
        const dot = document.getElementById('insp-dot');
        const name = document.getElementById('insp-name');
        const task = document.getElementById('insp-task');
        const badge = document.getElementById('insp-state');
        if (dot) dot.style.background = agent.color;
        if (name) name.innerText = agent.name;
        const roomLabel = ROOM_LABELS[resolveRoomKey(agent.zone)] || agent.zone || 'ATRIUM';
        if (task) task.innerText = `[${roomLabel}] ${agent.task || agent.title}`;
        if (badge) badge.innerText = `${agent.state} · ${agent.completed_count} done`;
    }

    function renderOpsPanel() {
        const scroll = document.getElementById('office-ops-scroll');
        if (!scroll || !state.snapshot) return;

        if (state.activeTab === 'tasks') {
            const tasks = state.snapshot.tasks || [];
            if (!tasks.length) {
                scroll.innerHTML = '<div class="office-empty-hint">No tasks yet. Select an agent and send a command, or convene a Meeting Mission.</div>';
                return;
            }
            scroll.innerHTML = tasks.slice(0, 25).map((t) => `
                <div class="office-task-card">
                    <div class="office-card-meta">
                        <span>@${escapeHtml(t.assigned_to)} · ${escapeHtml(t.kind)}</span>
                        <span class="office-status-tag ${escapeHtml(t.status)}">${escapeHtml(t.status)}</span>
                    </div>
                    <div class="office-card-title">${escapeHtml(t.title)}</div>
                    ${t.result ? `<div class="office-card-result">${escapeHtml(t.result)}</div>` : ''}
                </div>
            `).join('');
            return;
        }

        const feed = state.snapshot.feed || [];
        if (!feed.length) {
            scroll.innerHTML = '<div class="office-empty-hint">Agent communication log is empty.</div>';
            return;
        }
        scroll.innerHTML = feed.slice(0, 35).map((f) => `
            <div class="office-feed-item">
                <div class="office-card-meta">
                    <span>@${escapeHtml(f.from_agent)} → @${escapeHtml(f.to_agent)}</span>
                    <span>${escapeHtml(formatAgo(f.timestamp))}</span>
                </div>
                <div class="office-card-result" style="border-top:none; padding-top:0; margin-top:0; color: var(--office-text-primary);">${escapeHtml(f.message)}</div>
            </div>
        `).join('');
    }

    // ── Canvas Sprite Positions & Pixel Lab Renderer ────────────────────────
    // Walkable corridor graph through open doorways & around central furniture
    const ROOM_NODES = {
        // INTEL LAB (Top-Left, x < 524, y < 296)
        L1_W: [108, 256], L1_DESK: [228, 264], L1_E: [416, 268], L1_DOOR: [524, 272],
        // COMMAND DECK (Top-Center, 524..872, y < 294)
        CMD_DESK: [712, 162], CMD_BACK_E: [814, 162], CMD_SIDE_E: [814, 254],
        CMD_W: [584, 294], CMD_S: [695, 294], CMD_E: [806, 294],
        CMD_VIS_L: [644, 254], CMD_VIS_R: [748, 254],
        // UI & DEV LAB (Top-Right, x > 872, y < 296)
        R1_DOOR: [872, 272], R1_W: [926, 264], R1_K: [978, 258], R1_V: [1158, 258], R1_E: [1300, 258],
        // DATA / NET (Middle-Left, x < 524, 296..526)
        L2_W: [166, 504], L2_DESK: [308, 504], L2_E: [446, 504],
        L2_MAP: [334, 420], L2_MID: [426, 456], L2_DOOR: [524, 434],
        // IOT & MAKER (Middle-Right, x > 872, 296..526)
        R2_DOOR: [872, 444], R2_IN: [914, 454], R2_SW: [914, 514], R2_F: [978, 512], R2_DESK: [1064, 466], R2_E: [1288, 498],
        // SYS OPS (Bottom-Left, x < 524, y >= 526)
        L3_DOOR: [524, 558], L3_HALL: [512, 646], L3_CORNER: [490, 704],
        L3_DESK: [444, 708], L3_MID: [288, 716], L3_W: [136, 712],
        // MEDIA & QA (Bottom-Right, x > 872, y >= 526)
        R3_DOOR: [872, 558], R3_IN: [894, 588], R3_HALL: [894, 654],
        R3_DESK: [964, 692], R3_B: [1102, 692], R3_CAM: [1178, 688],
        // CENTRAL ATRIUM SPINE (524..872, y >= 294)
        AT_NW: [568, 314], AT_N: [695, 324], AT_NE: [834, 314],
        AT_ML: [562, 434], AT_MC: [695, 434], AT_MR: [846, 434],
        AT_SWL: [562, 548], AT_SWR: [846, 548],
        SOFA_W: [586, 496], SOFA_M: [660, 502], SOFA_E: [738, 496],
        BISTRO_S: [790, 540], BISTRO_E: [836, 496],
        LOB_W: [590, 592], LOB_C: [695, 592], LOB_E: [806, 592], LOB_DOOR: [695, 668],
    };

    const NODE_ROOM = {
        L1_W: 'intel_lab', L1_DESK: 'intel_lab', L1_E: 'intel_lab', L1_DOOR: 'intel_lab',
        CMD_DESK: 'command_deck', CMD_BACK_E: 'command_deck', CMD_SIDE_E: 'command_deck',
        CMD_W: 'command_deck', CMD_S: 'command_deck', CMD_E: 'command_deck',
        CMD_VIS_L: 'command_deck', CMD_VIS_R: 'command_deck',
        R1_DOOR: 'dev_lab', R1_W: 'dev_lab', R1_K: 'dev_lab', R1_V: 'dev_lab', R1_E: 'dev_lab',
        L2_W: 'data_net', L2_DESK: 'data_net', L2_E: 'data_net',
        L2_MAP: 'data_net', L2_MID: 'data_net', L2_DOOR: 'data_net',
        R2_DOOR: 'maker_iot', R2_IN: 'maker_iot', R2_SW: 'maker_iot', R2_F: 'maker_iot', R2_DESK: 'maker_iot', R2_E: 'maker_iot',
        L3_DOOR: 'sys_ops', L3_HALL: 'sys_ops', L3_CORNER: 'sys_ops',
        L3_DESK: 'sys_ops', L3_MID: 'sys_ops', L3_W: 'sys_ops',
        R3_DOOR: 'media_qa', R3_IN: 'media_qa', R3_HALL: 'media_qa',
        R3_DESK: 'media_qa', R3_B: 'media_qa', R3_CAM: 'media_qa',
        AT_NW: 'atrium', AT_N: 'atrium', AT_NE: 'atrium',
        AT_ML: 'atrium', AT_MC: 'atrium', AT_MR: 'atrium',
        AT_SWL: 'atrium', AT_SWR: 'atrium', SOFA_W: 'atrium', SOFA_M: 'atrium', SOFA_E: 'atrium',
        BISTRO_S: 'atrium', BISTRO_E: 'atrium',
        LOB_W: 'atrium', LOB_C: 'atrium', LOB_E: 'atrium', LOB_DOOR: 'atrium',
    };

    const ROOM_EDGES = {
        L1_W: ['L1_DESK'],
        L1_DESK: ['L1_W', 'L1_E'],
        L1_E: ['L1_DESK', 'L1_DOOR'],
        L1_DOOR: ['L1_E', 'AT_NW'],
        CMD_DESK: ['CMD_BACK_E'],
        CMD_BACK_E: ['CMD_DESK', 'CMD_SIDE_E'],
        CMD_SIDE_E: ['CMD_BACK_E', 'CMD_E', 'CMD_VIS_R'],
        CMD_W: ['CMD_VIS_L', 'CMD_S', 'AT_NW'],
        CMD_S: ['CMD_W', 'CMD_VIS_L', 'CMD_VIS_R', 'CMD_E', 'AT_N'],
        CMD_E: ['CMD_S', 'CMD_VIS_R', 'CMD_SIDE_E', 'AT_NE'],
        CMD_VIS_L: ['CMD_W', 'CMD_S', 'CMD_VIS_R'],
        CMD_VIS_R: ['CMD_S', 'CMD_E', 'CMD_VIS_L', 'CMD_SIDE_E'],
        R1_DOOR: ['AT_NE', 'R1_W'],
        R1_W: ['R1_DOOR', 'R1_K'],
        R1_K: ['R1_W', 'R1_V'],
        R1_V: ['R1_K', 'R1_E'],
        R1_E: ['R1_V'],
        L2_W: ['L2_DESK'],
        L2_DESK: ['L2_W', 'L2_E'],
        L2_E: ['L2_DESK', 'L2_MID'],
        L2_MAP: ['L2_MID'],
        L2_MID: ['L2_E', 'L2_MAP', 'L2_DOOR'],
        L2_DOOR: ['L2_MID', 'AT_ML'],
        R2_DOOR: ['AT_MR', 'R2_IN'],
        R2_IN: ['R2_DOOR', 'R2_SW', 'R2_DESK'],
        R2_SW: ['R2_IN', 'R2_F'],
        R2_F: ['R2_SW'],
        R2_DESK: ['R2_IN', 'R2_E'],
        R2_E: ['R2_DESK'],
        L3_DOOR: ['AT_SWL', 'L3_HALL'],
        L3_HALL: ['L3_DOOR', 'L3_CORNER'],
        L3_CORNER: ['L3_HALL', 'L3_DESK'],
        L3_DESK: ['L3_CORNER', 'L3_MID'],
        L3_MID: ['L3_DESK', 'L3_W'],
        L3_W: ['L3_MID'],
        R3_DOOR: ['AT_SWR', 'R3_IN'],
        R3_IN: ['R3_DOOR', 'R3_HALL'],
        R3_HALL: ['R3_IN', 'R3_DESK'],
        R3_DESK: ['R3_HALL', 'R3_B'],
        R3_B: ['R3_DESK', 'R3_CAM'],
        R3_CAM: ['R3_B'],
        AT_NW: ['L1_DOOR', 'CMD_W', 'AT_N', 'AT_ML'],
        AT_N: ['CMD_S', 'AT_NW', 'AT_NE'],
        AT_NE: ['CMD_E', 'R1_DOOR', 'AT_N', 'AT_MR'],
        AT_ML: ['L2_DOOR', 'AT_NW', 'AT_MC', 'SOFA_W', 'AT_SWL'],
        AT_MC: ['AT_ML', 'AT_MR'],
        AT_MR: ['R2_DOOR', 'AT_NE', 'AT_MC', 'SOFA_E', 'BISTRO_E', 'AT_SWR'],
        SOFA_W: ['AT_ML', 'AT_SWL', 'SOFA_M'],
        SOFA_M: ['SOFA_W', 'SOFA_E'],
        SOFA_E: ['AT_MR', 'AT_SWR', 'SOFA_M', 'BISTRO_S'],
        BISTRO_S: ['SOFA_E', 'AT_SWR', 'BISTRO_E'],
        BISTRO_E: ['AT_MR', 'BISTRO_S', 'AT_SWR'],
        AT_SWL: ['L3_DOOR', 'AT_ML', 'SOFA_W', 'LOB_W'],
        AT_SWR: ['R3_DOOR', 'AT_MR', 'SOFA_E', 'BISTRO_S', 'BISTRO_E', 'LOB_E'],
        LOB_W: ['AT_SWL', 'LOB_C'],
        LOB_C: ['LOB_W', 'LOB_E', 'LOB_DOOR'],
        LOB_E: ['AT_SWR', 'LOB_C'],
        LOB_DOOR: ['LOB_C'],
    };

    function getRoomAt(x, y) {
        if (x < 524) {
            if (y < 296) return 'intel_lab';
            if (y < 526) return 'data_net';
            return 'sys_ops';
        }
        if (x > 872) {
            if (y < 296) return 'dev_lab';
            if (y < 526) return 'maker_iot';
            return 'media_qa';
        }
        return y < 294 ? 'command_deck' : 'atrium';
    }

    function nearestRoomNode(x, y, roomFilter) {
        let bestId = null;
        let bestDist = Infinity;
        Object.entries(ROOM_NODES).forEach(([id, [nx, ny]]) => {
            if (roomFilter && NODE_ROOM[id] !== roomFilter) return;
            const d = Math.hypot(nx - x, ny - y);
            if (d < bestDist) {
                bestDist = d;
                bestId = id;
            }
        });
        return bestId || 'AT_MC';
    }

    function computeWalkPath(sx, sy, tx, ty) {
        const startRoom = getRoomAt(sx, sy);
        const goalRoom = getRoomAt(tx, ty);
        if (startRoom === goalRoom && Math.hypot(tx - sx, ty - sy) <= 26) {
            return [{ x: tx, y: ty }];
        }
        const startId = nearestRoomNode(sx, sy, startRoom);
        const goalId = nearestRoomNode(tx, ty, goalRoom);
        const waypoints = [];

        if (startId === goalId) {
            const [nx, ny] = ROOM_NODES[startId];
            waypoints.push({ x: nx, y: ny });
        } else {
            // Shortest path Dijkstra on ROOM_NODES
            const dist = { [startId]: 0 };
            const prev = {};
            const unvisited = new Set(Object.keys(ROOM_NODES));
            while (unvisited.size) {
                let u = null;
                unvisited.forEach((id) => {
                    if (u === null || (dist[id] ?? Infinity) < (dist[u] ?? Infinity)) u = id;
                });
                if (u === null || u === goalId || (dist[u] ?? Infinity) === Infinity) break;
                unvisited.delete(u);
                const [ux, uy] = ROOM_NODES[u];
                (ROOM_EDGES[u] || []).forEach((v) => {
                    if (!unvisited.has(v)) return;
                    const [vx, vy] = ROOM_NODES[v];
                    const alt = dist[u] + Math.hypot(vx - ux, vy - uy);
                    if (alt < (dist[v] ?? Infinity)) {
                        dist[v] = alt;
                        prev[v] = u;
                    }
                });
            }
            const chain = [];
            let cur = goalId;
            while (cur) {
                chain.unshift(cur);
                if (cur === startId) break;
                cur = prev[cur];
            }
            chain.forEach((id) => {
                const [nx, ny] = ROOM_NODES[id];
                waypoints.push({ x: nx, y: ny });
            });
        }
        waypoints.push({ x: tx, y: ty });
        return waypoints;
    }

    function setSpriteDestination(sp, newTx, newTy) {
        if (Math.hypot(newTx - sp.tx, newTy - sp.ty) <= 2) return;
        sp.tx = newTx;
        sp.ty = newTy;
        sp.path = computeWalkPath(sp.x, sp.y, newTx, newTy);
    }

    function resolveRoomKey(rawZone) {
        if (!rawZone) return 'lounge';
        if (SHARED_ROOM_SLOTS[rawZone] || rawZone === 'meeting' || rawZone === 'lounge') return rawZone;
        return LEGACY_ROOM_MAP[rawZone] || 'command_deck';
    }

    function pickFreeRoomSlot(roomId, selfSprite) {
        const pool = SHARED_ROOM_SLOTS[roomId];
        if (!pool || !pool.length) return null;
        if (selfSprite.slotRoom === roomId && typeof selfSprite.slotIdx === 'number' && pool[selfSprite.slotIdx]) {
            return { idx: selfSprite.slotIdx, slot: pool[selfSprite.slotIdx] };
        }
        const used = new Set();
        Object.values(state.sprites).forEach((other) => {
            if (other !== selfSprite && other.slotRoom === roomId && typeof other.slotIdx === 'number') {
                used.add(other.slotIdx);
            }
        });
        // Non-jarvis specialists prefer visitor briefing chairs when visiting Command Deck
        const order = (roomId === 'command_deck' && selfSprite.agent_id !== 'jarvis')
            ? [1, 2, 0]
            : pool.map((_, i) => i);
        const freeIdx = order.find((idx) => idx < pool.length && !used.has(idx));
        const chosen = freeIdx !== undefined ? freeIdx : Math.floor(Math.random() * pool.length);
        return { idx: chosen, slot: pool[chosen] };
    }

    function pickFreeChillSeat(selfSprite) {
        if (selfSprite.slotRoom === 'chill_seat' && typeof selfSprite.slotIdx === 'number' && CHILL_SEATS[selfSprite.slotIdx]) {
            return { idx: selfSprite.slotIdx, slot: CHILL_SEATS[selfSprite.slotIdx] };
        }
        const used = new Set();
        Object.values(state.sprites).forEach((other) => {
            if (other !== selfSprite && other.slotRoom === 'chill_seat' && typeof other.slotIdx === 'number') {
                used.add(other.slotIdx);
            }
        });
        const free = CHILL_SEATS.map((_, i) => i).filter((i) => !used.has(i));
        if (!free.length) return null;
        const chosen = free[Math.floor(Math.random() * free.length)];
        return { idx: chosen, slot: CHILL_SEATS[chosen] };
    }

    function syncLocalSprites(agents) {
        const now = performance.now();
        agents.forEach((a, idx) => {
            let sp = state.sprites[a.agent_id];
            const starterChill = CHILL_SEATS[idx];
            const home = (idx < 4 && starterChill) ? starterChill : LOUNGE_SPOTS[idx % LOUNGE_SPOTS.length];
            if (!sp) {
                sp = {
                    agent_id: a.agent_id,
                    x: home.x,
                    y: home.y,
                    tx: home.x,
                    ty: home.y,
                    path: [],
                    facing: home.dir === 'left' ? -1 : 1,
                    dir: home.dir || 'down',
                    restDir: home.dir || 'down',
                    restSit: Boolean(home.sit),
                    slotRoom: (idx < 4 && starterChill) ? 'chill_seat' : 'lounge',
                    slotIdx: (idx < 4 && starterChill) ? idx : null,
                    activeMon: null,
                    walkStep: 0,
                    nextRoamAt: now + 2000 + idx * 1100,
                    data: a,
                };
                state.sprites[a.agent_id] = sp;
            } else {
                sp.data = a;
            }

            if (a.state === 'MEETING' || a.zone === 'meeting') {
                const seat = MEETING_SEATS[a.agent_id] || { x: 660, y: 488, dir: 'down', sit: true };
                sp.slotRoom = 'meeting';
                sp.slotIdx = null;
                sp.activeMon = null;
                sp.restDir = seat.dir || 'down';
                sp.restSit = Boolean(seat.sit);
                setSpriteDestination(sp, seat.x, seat.y);
            } else if (a.state !== 'IDLE') {
                const targetRoom = resolveRoomKey(a.zone && a.zone !== 'lounge' ? a.zone : a.desk_zone);
                const picked = pickFreeRoomSlot(targetRoom, sp);
                if (picked) {
                    sp.slotRoom = targetRoom;
                    sp.slotIdx = picked.idx;
                    sp.activeMon = picked.slot.mon || null;
                    sp.restDir = picked.slot.dir || 'up';
                    sp.restSit = Boolean(picked.slot.sit);
                    setSpriteDestination(sp, picked.slot.x, picked.slot.y);
                }
            } else if ((!sp.path || sp.path.length === 0) && now >= sp.nextRoamAt) {
                const roamRoom = ROAM_ROOM_POOL[Math.floor(Math.random() * ROAM_ROOM_POOL.length)];
                if (roamRoom === 'chill_seat') {
                    const chill = pickFreeChillSeat(sp);
                    if (chill) {
                        sp.slotRoom = 'chill_seat';
                        sp.slotIdx = chill.idx;
                        sp.activeMon = null;
                        sp.restDir = chill.slot.dir || 'down';
                        sp.restSit = true;
                        setSpriteDestination(sp, chill.slot.x, chill.slot.y);
                    }
                } else if (roamRoom === 'lounge') {
                    const spot = LOUNGE_SPOTS[Math.floor(Math.random() * LOUNGE_SPOTS.length)];
                    sp.slotRoom = 'lounge';
                    sp.slotIdx = null;
                    sp.activeMon = null;
                    sp.restDir = spot.dir || 'down';
                    sp.restSit = Boolean(spot.sit);
                    setSpriteDestination(
                        sp,
                        Math.round(spot.x + (Math.random() * 8 - 4)),
                        Math.round(spot.y + (Math.random() * 6 - 3))
                    );
                } else {
                    const picked = pickFreeRoomSlot(roamRoom, sp);
                    if (picked) {
                        sp.slotRoom = roamRoom;
                        sp.slotIdx = picked.idx;
                        sp.activeMon = null;
                        sp.restDir = picked.slot.dir || 'up';
                        sp.restSit = Boolean(picked.slot.sit);
                        setSpriteDestination(sp, picked.slot.x, picked.slot.y);
                    }
                }
                sp.nextRoamAt = now + 7000 + Math.random() * 8000;
            }
        });
    }

    function handleCanvasClick(e) {
        const canvas = document.getElementById('ai-office-canvas');
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const scaleX = OFFICE_W / rect.width;
        const scaleY = OFFICE_H / rect.height;
        const cx = (e.clientX - rect.left) * scaleX;
        const cy = (e.clientY - rect.top) * scaleY;

        let closest = null;
        let minDist = 56;
        Object.values(state.sprites).forEach((sp) => {
            const d = Math.hypot(cx - sp.x, cy - (sp.y - 26));
            if (d < minDist) {
                minDist = d;
                closest = sp.agent_id;
            }
        });
        if (closest) selectAgent(closest);
    }

    function startCanvasLoop() {
        const canvas = document.getElementById('ai-office-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const backdrop = getMindspaceBackdrop();
        let lastTs = performance.now();

        function tick(nowTs) {
            if (!state.isOpen) return;
            const dtMs = Math.min(50, Math.max(4, nowTs - lastTs));
            lastTs = nowTs;
            const dtScale = dtMs / 16.6667;
            state.frame += 1;
            ctx.imageSmoothingEnabled = true;
            if (studioBackdropImg && studioBackdropImg.complete && studioBackdropImg.naturalWidth > 0) {
                ctx.drawImage(studioBackdropImg, 0, 0, OFFICE_W, OFFICE_H);
            } else {
                ctx.drawImage(backdrop, 0, 0);
            }
            drawMindspaceAnimations(ctx);
            updateAndDrawAgents(ctx, dtScale);
            state.rafId = requestAnimationFrame(tick);
        }
        state.rafId = requestAnimationFrame(tick);
    }

    let mindspaceBackdropCanvas = null;
    const studioBackdropImg = new Image();
    studioBackdropImg.src = '/static/mindspace_studio_3d.jpg?v=3';

    const STUDIO_SPARKS = [
        { x: 941, y: 406, col: '#38bdf8', p: 18, ph: 1 },
        { x: 1005, y: 406, col: '#fb923c', p: 22, ph: 7 },
        { x: 1058, y: 410, col: '#38bdf8', p: 25, ph: 4 },
        { x: 215, y: 402, col: '#4ade80', p: 16, ph: 3 },
        { x: 215, y: 412, col: '#38bdf8', p: 20, ph: 9 },
        { x: 274, y: 116, col: '#facc15', p: 32, ph: 2 },
    ];

    function getMindspaceBackdrop() {
        if (mindspaceBackdropCanvas) return mindspaceBackdropCanvas;
        const cnv = document.createElement('canvas');
        cnv.width = OFFICE_W;
        cnv.height = OFFICE_H;
        const c = cnv.getContext('2d');
        const grad = c.createLinearGradient(0, 0, 0, OFFICE_H);
        grad.addColorStop(0, '#2b1e1a');
        grad.addColorStop(1, '#1a1210');
        c.fillStyle = grad;
        c.fillRect(0, 0, OFFICE_W, OFFICE_H);
        c.fillStyle = 'rgba(255, 224, 178, 0.45)';
        c.font = 'bold 14px "JetBrains Mono", monospace';
        c.textAlign = 'center';
        c.fillText('LOADING 3D MINDSPACE DIORAMA...', OFFICE_W / 2, OFFICE_H / 2);
        mindspaceBackdropCanvas = cnv;
        return cnv;
    }

    function drawMindspaceAnimations(ctx) {
        const f = state.frame;
        const agents = (state.snapshot && state.snapshot.agents) || [];
        let meetingActive = false;
        agents.forEach((a) => {
            if (a.state === 'MEETING' || a.zone === 'meeting') meetingActive = true;
        });

        // 1. Subtle sunlit window sparkles drifting down from panoramic skyline
        ctx.save();
        for (let i = 0; i < 16; i++) {
            const mx = ((i * 89 + Math.sin(f * 0.015 + i) * 18) % (OFFICE_W - 80)) + 40;
            const my = ((i * 37 + f * 0.35) % 240) + 45;
            ctx.fillStyle = 'rgba(255, 248, 214, 0.28)';
            ctx.fillRect(Math.round(mx), Math.round(my), 2, 2);
        }

        // 2. Espresso machine steam wisps in central atrium coffee bar (x ~ 646, y ~ 368)
        for (let s = 0; s < 3; s++) {
            const phase = (f * 0.04 + s * 2.1) % 3;
            const sx = 644 + s * 5 + Math.sin(f * 0.07 + s) * 2;
            const sy = 368 - phase * 7;
            ctx.fillStyle = `rgba(255, 255, 255, ${(0.32 - phase * 0.1).toFixed(2)})`;
            ctx.fillRect(Math.round(sx), Math.round(sy), 3, 3);
        }

        // 3. Light up whichever station monitor/rig a working agent has dynamically occupied!
        Object.values(state.sprites).forEach((sp, idx) => {
            const owner = sp.data;
            const working = owner && owner.state !== 'IDLE' && owner.state !== 'MEETING';
            const r = sp.activeMon;
            if (!working || !r) return;
            ctx.fillStyle = owner.color;
            ctx.globalAlpha = 0.22 + 0.08 * Math.sin(f * 0.14 + idx);
            ctx.fillRect(r.x - 3, r.y - 3, r.w + 6, r.h + 6);
            ctx.globalAlpha = 0.72;
            ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
            for (let ln = 0; ln < 3; ln++) {
                const lw = Math.min(r.w - 8, 10 + Math.floor(((f * 0.4 + ln * 7 + idx * 5) % Math.max(8, r.w - 10))));
                ctx.fillRect(r.x + 4, r.y + 5 + ln * 6, lw, 2);
            }
        });
        ctx.globalAlpha = 1;

        // 4. Blinking 3D printer & server rack indicator sparks
        STUDIO_SPARKS.forEach((sp) => {
            if ((Math.floor(f / sp.p) + sp.ph) % 3 !== 0) return;
            ctx.fillStyle = sp.col;
            ctx.fillRect(sp.x, sp.y, 3, 3);
        });

        // 5. Meeting Lounge aura on bistro table & sofa rug during active meeting
        if (meetingActive) {
            const pulse = (Math.sin(f * 0.08) + 1) / 2;
            ctx.strokeStyle = '#22d3ee';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.ellipse(662, 520, 74 + pulse * 5, 36 + pulse * 3, 0, 0, Math.PI * 2);
            ctx.stroke();

            ctx.fillStyle = 'rgba(10, 14, 22, 0.86)';
            ctx.fillRect(606, 444, 112, 16);
            ctx.font = 'bold 10px "JetBrains Mono", monospace';
            ctx.textAlign = 'center';
            ctx.fillStyle = '#67e8f9';
            ctx.fillText('MEETING // ACTIVE', 662, 456);
        }
        ctx.restore();
    }

    const spriteFrameCache = {};

    function buildMatrixCanvas(rows, palette) {
        const cols = rows[0].length;
        const rowCount = rows.length;
        const cnv = document.createElement('canvas');
        cnv.width = cols + 2;
        cnv.height = rowCount + 4;
        const sctx = cnv.getContext('2d');
        for (let r = 0; r < rowCount; r++) {
            const row = rows[r];
            for (let c = 0; c < cols; c++) {
                const ch = row[c];
                if (ch === '.' || !palette[ch]) continue;
                sctx.fillStyle = palette[ch];
                sctx.fillRect(c + 1, r + 2, 1, 1);
            }
        }
        return cnv;
    }

    function buildSpriteCanvas(spec, stepSign, matrixRows) {
        const rows = matrixRows || spec.rows;
        const palette = spec.palette;
        const cols = rows[0].length;
        const rowCount = rows.length;
        const legStart = Math.floor(rowCount * 0.78);
        const armStart = Math.floor(rowCount * 0.45);
        const armEnd = Math.floor(rowCount * 0.72);
        const armBand = Math.min(4, Math.floor(cols * 0.25));
        const midX = Math.floor(cols / 2);

        const cnv = document.createElement('canvas');
        cnv.width = cols + 2;
        cnv.height = rowCount + 4;
        const sctx = cnv.getContext('2d');
        const bodyBob = stepSign !== 0 ? -1 : 0;

        for (let r = 0; r < rowCount; r++) {
            const row = rows[r];
            for (let c = 0; c < cols; c++) {
                const ch = row[c];
                if (ch === '.' || !palette[ch]) continue;
                let dx = 1;
                let dy = 2;

                if (stepSign !== 0 && r >= legStart) {
                    const isLeftFoot = c < midX;
                    const lift = isLeftFoot ? stepSign : -stepSign;
                    dy += lift < 0 ? -2 : 1;
                    dx += isLeftFoot ? stepSign : -stepSign;
                } else {
                    dy += bodyBob;
                    if (stepSign !== 0 && r >= armStart && r <= armEnd && (c <= armBand || c >= cols - 1 - armBand)) {
                        const isLeftArm = c < midX;
                        dy += isLeftArm ? -stepSign : stepSign;
                    }
                }
                sctx.fillStyle = palette[ch];
                sctx.fillRect(c + dx, r + dy, 1, 1);
            }
        }
        return cnv;
    }

    function buildSittingCanvas(spec, matrixRows, poseDir) {
        const rows = matrixRows || spec.rows;
        const palette = spec.palette;
        const cols = rows[0].length;
        const rowCount = rows.length;
        const hipRow = Math.floor(rowCount * 0.72);
        const legStart = Math.floor(rowCount * 0.78);
        const seatDrop = poseDir === 'side' ? 4 : 5;
        const midX = Math.floor(cols / 2);

        const cnv = document.createElement('canvas');
        cnv.width = cols + (poseDir === 'side' ? 6 : 4);
        cnv.height = rowCount + 4;
        const sctx = cnv.getContext('2d');
        const baseX = poseDir === 'side' ? 1 : 2;

        for (let r = 0; r < rowCount; r++) {
            const row = rows[r];
            for (let c = 0; c < cols; c++) {
                const ch = row[c];
                if (ch === '.' || !palette[ch]) continue;
                let dx = baseX;
                let dy = 2 + seatDrop;

                if (poseDir === 'side') {
                    // L-shaped profile: knees project +3..+4px forward on cushion, lower calves drop to bottom
                    if (r >= hipRow && r < legStart + 2) {
                        dx += 3;
                        dy = 2 + seatDrop - Math.floor((r - hipRow) * 0.65);
                    } else if (r >= legStart + 2) {
                        dx += 4;
                        dy = 2 + Math.min(4, rowCount - r);
                        if (r < rowCount - 3) continue; // compress calf height into seated knees
                    }
                } else {
                    // Front / Back seated lap: drop upper body into cushion & tuck bent knees/feet
                    if (r >= legStart && r < rowCount - 3) {
                        continue; // skip mid-shin standing height to show bent seated lap
                    }
                    if (r >= rowCount - 3) {
                        dy = 2 + 1; // bring tucked shoes right under hip lap at bottom anchor
                        if (poseDir === 'down') {
                            dx += (c < midX ? -1 : 1); // subtle seated knee/foot flare facing viewer
                        }
                    } else if (r >= hipRow) {
                        dy = 2 + seatDrop;
                        if (poseDir === 'down') {
                            dx += (c < midX ? -1 : 1);
                        }
                    }
                }
                const outY = Math.min(cnv.height - 2, r + dy);
                sctx.fillStyle = palette[ch];
                sctx.fillRect(c + dx, outY, 1, 1);
            }
        }
        return cnv;
    }

    function getSpriteFrame(agentId, isMoving, walkStep, dir, isSeated) {
        if (!spriteFrameCache[agentId]) {
            const spec = PIXEL_CAST[agentId] || PIXEL_CAST.jarvis;
            const upRows = spec.up || spec.rows;
            const sideIdle = spec.sideIdle || spec.rows;
            const sideWalkA = spec.sideWalkA || sideIdle;
            const sideWalkB = spec.sideWalkB || sideIdle;
            spriteFrameCache[agentId] = {
                down: {
                    idle: buildSpriteCanvas(spec, 0, spec.rows),
                    walkA: buildSpriteCanvas(spec, -1, spec.rows),
                    walkB: buildSpriteCanvas(spec, 1, spec.rows),
                },
                up: {
                    idle: buildSpriteCanvas(spec, 0, upRows),
                    walkA: buildSpriteCanvas(spec, -1, upRows),
                    walkB: buildSpriteCanvas(spec, 1, upRows),
                },
                side: {
                    idle: buildMatrixCanvas(sideIdle, spec.palette),
                    walkA: buildMatrixCanvas(sideWalkA, spec.palette),
                    walkB: buildMatrixCanvas(sideWalkB, spec.palette),
                },
                sit: {
                    down: buildSittingCanvas(spec, spec.rows, 'down'),
                    up: buildSittingCanvas(spec, upRows, 'up'),
                    side: buildSittingCanvas(spec, sideIdle, 'side'),
                },
            };
        }
        const entry = spriteFrameCache[agentId];
        const poseKey = (dir === 'left' || dir === 'right') ? 'side' : (dir === 'up' ? 'up' : 'down');
        if (!isMoving && isSeated) {
            return entry.sit[poseKey];
        }
        const bank = entry[poseKey];
        if (!isMoving) return bank.idle;
        const phase = Math.floor(walkStep / 8.5) % 4;
        if (phase === 0) return bank.walkA;
        if (phase === 2) return bank.walkB;
        return bank.idle;
    }

    function drawPixelCharacter(ctx, x, y, agentId, isMoving, isBusy, walkStep, dir, isSeated) {
        const idleBob = !isMoving
            ? (isSeated
                ? (isBusy ? (Math.floor(state.frame / 12) % 2) * -1 : 0)
                : (isBusy ? (Math.floor(state.frame / 10) % 2) * 2 : (Math.floor(state.frame / 26) % 2)))
            : 0;
        const frameCanvas = getSpriteFrame(agentId, isMoving, walkStep, dir, isSeated);
        const drawW = Math.round(frameCanvas.width * SPRITE_SCALE);
        const drawH = Math.round(frameCanvas.height * SPRITE_SCALE);
        const cx = Math.round(x);
        const oy = Math.round(y - ((frameCanvas.height - 4) * SPRITE_SCALE) - idleBob + 4);

        ctx.save();
        ctx.imageSmoothingEnabled = false;
        ctx.translate(cx, oy);
        if (dir === 'left') {
            ctx.scale(-1, 1);
        }
        ctx.drawImage(frameCanvas, Math.round(-drawW / 2), 0, drawW, drawH);
        ctx.restore();
    }

    function drawSpeechBubble(ctx, x, y, text, accentColor, spriteHeight) {
        if (!text) return;
        const clean = text.length > 36 ? text.slice(0, 35) + '…' : text;
        ctx.font = 'bold 13px "JetBrains Mono", monospace';
        const w = Math.min(340, ctx.measureText(clean).width + 22);
        const bx = Math.max(24, Math.min(OFFICE_W - w - 24, x - w / 2));
        const by = Math.max(24, y - Math.round((spriteHeight || 42) * SPRITE_SCALE) - 34);

        ctx.fillStyle = 'rgba(10, 14, 22, 0.94)';
        ctx.fillRect(bx, by, w, 25);
        ctx.strokeStyle = accentColor;
        ctx.lineWidth = 1.5;
        ctx.strokeRect(bx, by, w, 25);

        ctx.fillStyle = '#f4f5f6';
        ctx.textAlign = 'left';
        ctx.fillText(clean, bx + 10, by + 17);
    }

    const WALK_SPEED_PX_PER_FRAME = 1.45; // smooth natural RPG walk across 1376x768 3D studio

    function updateAndDrawAgents(ctx, dtScale) {
        const stepBudget = WALK_SPEED_PX_PER_FRAME * (dtScale || 1);
        const list = Object.values(state.sprites).sort((a, b) => a.y - b.y);

        list.forEach((sp) => {
            if (!sp.path || sp.path.length === 0) {
                if (Math.hypot(sp.tx - sp.x, sp.ty - sp.y) > 2.2) {
                    sp.path = computeWalkPath(sp.x, sp.y, sp.tx, sp.ty);
                }
            }

            let moving = false;
            let remaining = stepBudget;
            while (sp.path && sp.path.length > 0 && remaining > 0.01) {
                const wp = sp.path[0];
                const dx = wp.x - sp.x;
                const dy = wp.y - sp.y;
                const dist = Math.hypot(dx, dy);
                if (dist > 0.25) {
                    const adx = Math.abs(dx);
                    const ady = Math.abs(dy);
                    const isHoriz = (sp.dir === 'left' || sp.dir === 'right')
                        ? adx >= ady * 0.72
                        : adx >= ady * 1.15;
                    sp.dir = isHoriz ? (dx < 0 ? 'left' : 'right') : (dy < 0 ? 'up' : 'down');
                    sp.facing = sp.dir === 'left' ? -1 : 1;
                }
                if (dist <= remaining) {
                    sp.x = wp.x;
                    sp.y = wp.y;
                    sp.walkStep = (sp.walkStep || 0) + dist;
                    remaining -= dist;
                    sp.path.shift();
                    moving = true;
                } else {
                    const vx = (dx / dist) * remaining;
                    const vy = (dy / dist) * remaining;
                    sp.x += vx;
                    sp.y += vy;
                    sp.walkStep = (sp.walkStep || 0) + remaining;
                    remaining = 0;
                    moving = true;
                }
            }
            let isSeated = false;
            if (!moving) {
                const atTarget = Math.hypot(sp.x - sp.tx, sp.y - sp.ty) < 8;
                sp.dir = (atTarget && sp.restDir) ? sp.restDir : 'down';
                sp.facing = sp.dir === 'left' ? -1 : 1;
                isSeated = atTarget && Boolean(sp.restSit);
            }

            const a = sp.data;
            const isSelected = a.agent_id === state.selectedAgent;
            const isBusy = a.state !== 'IDLE';
            const cast = PIXEL_CAST[a.agent_id];
            const displayLabel = cast ? cast.bracket : a.name;

            // Grounded 3D drop shadow + holographic selection ring (subtle cushion ring when seated)
            ctx.fillStyle = isSeated ? 'rgba(14, 8, 6, 0.24)' : 'rgba(14, 8, 6, 0.42)';
            ctx.beginPath();
            ctx.ellipse(sp.x, sp.y + (isSeated ? 1 : 4), isSeated ? 19 : 22, isSeated ? 6 : 7.5, 0, 0, Math.PI * 2);
            ctx.fill();

            ctx.strokeStyle = isSelected ? '#ffffff' : a.color;
            ctx.lineWidth = isSelected ? 2.4 : (isSeated ? 1.2 : 1.6);
            ctx.globalAlpha = isSeated && !isSelected && !isBusy ? 0.55 : 1;
            ctx.beginPath();
            ctx.ellipse(sp.x, sp.y + (isSeated ? 1 : 4), isBusy ? 26 : 22, isBusy ? 9 : 7.5, 0, 0, Math.PI * 2);
            ctx.stroke();
            ctx.globalAlpha = 1;

            drawPixelCharacter(ctx, sp.x, sp.y, a.agent_id, moving, isBusy, sp.walkStep || 0, sp.dir || 'down', isSeated);

            // Retro Bracketed Nameplate + Live State chip
            ctx.font = 'bold 11px "JetBrains Mono", monospace';
            const lblW = ctx.measureText(displayLabel).width + 12;
            ctx.fillStyle = 'rgba(10, 6, 20, 0.86)';
            ctx.fillRect(Math.round(sp.x - lblW / 2), Math.round(sp.y + 10), Math.round(lblW), 16);
            ctx.textAlign = 'center';
            ctx.fillStyle = isSelected ? '#ffffff' : a.color;
            ctx.fillText(displayLabel, sp.x, sp.y + 22);

            if (isBusy) {
                ctx.font = 'bold 10px "JetBrains Mono", monospace';
                ctx.fillStyle = '#00d2ff';
                ctx.fillText(`[${a.state}]`, sp.x, sp.y + 37);
            }

            if (a.bubble) {
                drawSpeechBubble(ctx, sp.x, sp.y, a.bubble, a.color, cast ? cast.rows.length : 42);
            }
        });
    }
})();
