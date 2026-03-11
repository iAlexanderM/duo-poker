RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
SUITS = ['h', 'd', 'c', 's']
SUIT_SYMBOLS = {'h': '♥', 'd': '♦', 'c': '♣', 's': '♠'}

ALL_POSITIONS = ['UTG', 'UTG+1', 'UTG+2', 'MP', 'MP+1', 'CO', 'BTN', 'SB', 'BB']

POSITION_COORDS = {
    'UTG': (350, 50),
    'UTG+1': (497, 91),
    'UTG+2': (576, 195),
    'MP': (549, 312),
    'MP+1': (428, 389),
    'CO': (272, 389),
    'BTN': (151, 312),
    'SB': (124, 195),
    'BB': (203, 91),
}

PREFLOP_CHARTS = {
    'UTG': {
        'pairs': ['AA', 'KK', 'QQ', 'JJ', 'TT'],
        'suited': ['AKs', 'AQs', 'AJs', 'ATs', 'KQs'],
        'offsuit': ['AKo', 'AQo']
    },
    'UTG+1': {
        'pairs': ['AA', 'KK', 'QQ', 'JJ', 'TT', '99'],
        'suited': ['AKs', 'AQs', 'AJs', 'ATs', 'KQs', 'KJs', 'QJs'],
        'offsuit': ['AKo', 'AQo', 'AJo']
    },
    'UTG+2': {
        'pairs': ['AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88'],
        'suited': ['AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'KQs', 'KJs', 'KTs', 'QJs', 'QTs', 'JTs'],
        'offsuit': ['AKo', 'AQo', 'AJo', 'ATo', 'KQo']
    },
    'MP': {
        'pairs': ['AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77'],
        'suited': ['AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'KQs', 'KJs', 'KTs', 'K9s', 'QJs', 'QTs', 'Q9s', 'JTs',
                   'J9s', 'T9s'],
        'offsuit': ['AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'KQo', 'KJo', 'QJo']
    },
    'MP+1': {
        'pairs': ['AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66'],
        'suited': ['AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'QJs', 'QTs',
                   'Q9s', 'Q8s', 'JTs', 'J9s', 'J8s', 'T9s', 'T8s', '98s'],
        'offsuit': ['AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'A8o', 'KQo', 'KJo', 'KTo', 'QJo', 'QTo', 'JTo']
    },
    'CO': {
        'pairs': ['AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55'],
        'suited': ['AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'KQs', 'KJs', 'KTs', 'K9s', 'K8s',
                   'K7s', 'QJs', 'QTs', 'Q9s', 'Q8s', 'JTs', 'J9s', 'J8s', 'T9s', 'T8s', '98s', '97s', '87s'],
        'offsuit': ['AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'A8o', 'KQo', 'KJo', 'KTo', 'K9o', 'QJo', 'QTo', 'JTo']
    },
    'BTN': {
        'pairs': ['AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22'],
        'suited': ['AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                   'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s', 'QJs', 'QTs', 'Q9s', 'Q8s', 'Q7s', 'JTs',
                   'J9s', 'J8s', 'J7s', 'T9s', 'T8s', 'T7s', '98s', '97s', '96s', '87s', '86s', '76s', '75s', '65s',
                   '64s', '54s'],
        'offsuit': ['AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'A8o', 'A7o', 'A6o', 'A5o', 'A4o', 'A3o', 'A2o',
                    'KQo', 'KJo', 'KTo', 'K9o', 'K8o', 'K7o', 'QJo', 'QTo', 'Q9o', 'JTo', 'J9o', 'T9o', '98o', '87o',
                    '76o']
    },
    'SB': {
        'pairs': ['AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22'],
        'suited': ['AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                   'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s', 'K4s', 'QJs', 'QTs', 'Q9s', 'Q8s', 'Q7s',
                   'Q6s', 'JTs', 'J9s', 'J8s', 'J7s', 'J6s', 'T9s', 'T8s', 'T7s', 'T6s', '98s', '97s', '96s', '95s',
                   '87s', '86s', '85s', '76s', '75s', '74s', '65s', '64s', '63s', '54s', '53s'],
        'offsuit': ['AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'A8o', 'A7o', 'A6o', 'A5o', 'A4o', 'A3o', 'A2o',
                    'KQo', 'KJo', 'KTo', 'K9o', 'K8o', 'K7o', 'K6o', 'QJo', 'QTo', 'Q9o', 'Q8o', 'JTo', 'J9o', 'J8o',
                    'T9o', 'T8o', '98o', '97o', '87o', '86o', '76o', '75o', '65o', '64o', '54o']
    },
    'BB': {
        'pairs': ['AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22'],
        'suited': ['AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                   'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s', 'K4s', 'K3s', 'QJs', 'QTs', 'Q9s', 'Q8s',
                   'Q7s', 'Q6s', 'Q5s', 'JTs', 'J9s', 'J8s', 'J7s', 'J6s', 'J5s', 'T9s', 'T8s', 'T7s', 'T6s', 'T5s',
                   '98s', '97s', '96s', '95s', '94s', '87s', '86s', '85s', '84s', '76s', '75s', '74s', '73s', '65s',
                   '64s', '63s', '62s', '54s', '53s', '52s'],
        'offsuit': ['AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'A8o', 'A7o', 'A6o', 'A5o', 'A4o', 'A3o', 'A2o',
                    'KQo', 'KJo', 'KTo', 'K9o', 'K8o', 'K7o', 'K6o', 'K5o', 'K4o', 'QJo', 'QTo', 'Q9o', 'Q8o', 'Q7o',
                    'Q6o', 'JTo', 'J9o', 'J8o', 'J7o', 'J6o', 'T9o', 'T8o', 'T7o', 'T6o', '98o', '97o', '96o', '95o',
                    '87o', '86o', '85o', '76o', '75o', '74o', '65o', '64o', '63o', '54o', '53o']
    }
}
