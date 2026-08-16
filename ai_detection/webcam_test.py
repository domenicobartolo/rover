import cv2

def main():
    cap = cv2.VideoCapture(0) #0=webcam di default

    if not cap.isOpened():
        print("Impossibile accedere alla webcam")
        return
    
    print("Webcam aperta correttamente. Premi q per uscire")

    while True: #legge e mostra un frame alla volta, ret è un booleano, True se il frame è letto correttamente, frame: l'immagine catturata dalla webcam in quel momento
        ret, frame = cap.read()
        if not ret:
            print("Errore nella lettura del frame")
            break
        
        cv2.imshow("Webcam test", frame) #apre una finestra Webcam test e ci disegna dentro il frame catturato

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()