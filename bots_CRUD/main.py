import threading
from bots.bots_1 import ejecutar_bot1
from bots.bots_2 import ejecutar_bot2
from bots.bots_3 import ejecutar_bot3

def main():
    stop_event = threading.Event()

    bots = [
        threading.Thread(
            target = ejecutar_bot1,
            args = (stop_event,),
            name = "Bot-1"
        ),
        
        threading.Thread(
            target = ejecutar_bot2,
            args = (stop_event,),
            name = "Bot-2"
        ),
        
        threading.Thread(
            target = ejecutar_bot3,
            args = (stop_event,),
            name = "Bot-3"
        ), 
    ]

    print("\n =========== ")
    print(" SISTEMA DE BOTS - VETERINARIA")
    print("============")
    print("Inicindo los bots...\n")

    for bot in bots:
        bot.start()

    try:
        for bot in bots:
            bot.join()

    except KeyboardInterrupt:
        print("\n\nSe solicitó detener el sistema...")

        stop_event.set()

        for bot in bots:
            bot.join()

    print("\n==========")
    print(" TODOS LOS BOTS HAN FINALIZADO ")
    print("==========")

if __name__ == "__main__":
    main()