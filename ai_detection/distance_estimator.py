#APPROCCIO MONOCULARE: stima della distanza di una persona dalla camera, partendo dall'altezza in pixel del bb rilevato
#Formula: distanza = (altezza_persona * focale)/ altezza_bb_pixel

#altezza media 
person_height = 1.70

#valore di focale approssimato per webcam 
focal_length=700

def estimate_distance(bb_height):
    if bb_height<=0:
        return None
    distance= (person_height * focal_length)/ bb_height
    return (distance)