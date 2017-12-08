# vim:ts=4:sts=4:sw=4:expandtab

def parse_float_with_modifiers(x, modifiers):
    modifier = 1
    x = x.strip().lower()
    while len(x) > 0 and x[-1] in modifiers :
        modifier *= modifiers[x[-1]]
        x = x[:-1]
    return float(x) * modifier

def parse_time(x) :
    return parse_float_with_modifiers(x, {
        's' : 1,
        'm' : 10**-3,
        'µ' : 10**-6,
        'n' : 10**-9,
    })

def parse_memory(x):
    return int(round(parse_float_with_modifiers(x, {
        'b' : 1,
        'k' : 1024,
        'm' : 1024**2,
        'g' : 1024**3,
        't' : 1024**4,
        'p' : 1024**5,
    })))
