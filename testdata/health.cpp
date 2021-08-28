/*.$file${.::health.cpp} vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv*/
/*
* Model: health.qm
* File:  ${.::health.cpp}
*
*/
/*.$endhead${.::health.cpp} ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^*/
#include "qhsm.h"
#include "health.h"
#include "eventHandlers.h"
#include <stdint.h>
//Q_DEFINE_THIS_FILE
/* global-scope definitions -----------------------------------------*/
QHsm * const the_health = (QHsm *) &health; /* the opaque pointer */

/*.$skip${QP_VERSION} vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv*/
/*. Check for the minimum required QP version */
#if (QP_VERSION < 690U) || (QP_VERSION != ((QP_RELEASE^4294967295U) % 0x3E8U))
#error qpc version 6.9.0 or higher required
#endif
/*.$endskip${QP_VERSION} ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^*/
/*.$define${SMs::Health_ctor} vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv*/
/*.${SMs::Health_ctor} .....................................................*/
void Health_ctor(
    unsigned int health,
    unsigned int State,
    unsigned int god_pause)
{
    Health *me = &health;
         me->health = health;
        me->count = 0;
        me->god_pause=god_pause;
        switch (State) {
            case SIMPLE: {
                me->StartState =
                (QStateHandler)&Health_simple;
                break;
            }
            case GOD_READY: {
                me->StartState =
                (QStateHandler)&Health_god_ready;
                break;
            }
            case GOD: {
                me->StartState =
                (QStateHandler)&Health_god;
                break;
            }
            case DEAD: {
                me->StartState =
                (QStateHandler)&Health_god;
                break;
            }
            default:
                me->StartState =
                (QStateHandler)&Health_simple;
        }
    QHsm_ctor(&me->super, Q_STATE_CAST(&Health_initial));
}
/*.$enddef${SMs::Health_ctor} ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^*/
/*.$define${SMs::Health} vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv*/
/*.${SMs::Health} ..........................................................*/
/*.${SMs::Health::SM} ......................................................*/
QState Health_initial(Health * const me, void const * const par) {
    /*.${SMs::Health::SM::initial} */
    return Q_TRAN(&Health_simple);
}
/*.${SMs::Health::SM::global} ..............................................*/
QState Health_global(Health * const me, QEvt const * const e) {
    QState status_;
    switch (e->sig) {

#ifdef DESKTOP
        /*.${SMs::Health::SM::global::TERMINATE} */
        case TERMINATE_SIG: {
            status_ = Q_TRAN(&Health_final);
            break;
        }
#endif /* def DESKTOP */

        default: {
            status_ = Q_SUPER(&QHsm_top);
            break;
        }
    }
    return status_;
}
/*.${SMs::Health::SM::global::alive} .......................................*/
QState Health_alive(Health * const me, QEvt const * const e) {
    QState status_;
    switch (e->sig) {
        /*.${SMs::Health::SM::global::alive} */
        case Q_ENTRY_SIG: {
            #ifdef DESKTOP
            printf("Entered state alive");
            #endif /* def DESKTOP */
            SetHealth(DEFAULT_HP)
            StartTramsmitForPath();
            SetColor(LIGHT_GREEN);
            SaveHealth();
            status_ = Q_HANDLED();
            break;
        }
        /*.${SMs::Health::SM::global::alive} */
        case Q_EXIT_SIG: {
            #ifdef DESKTOP
            printf("Exited state alive");
            #endif /* def DESKTOP */

            status_ = Q_HANDLED();
            break;
        }
        /*.${SMs::Health::SM::global::alive::MONSTER_SIGNAl} */
        case MONSTER_SIGNAl_SIG: {
            MonsterVibro();
            status_ = Q_HANDLED();
            break;
        }
        /*.${SMs::Health::SM::global::alive::PILL_HEAL} */
        case PILL_HEAL_SIG: {
            SetHealth(DEFAULT_HP);
            ClearPill();
            status_ = Q_HANDLED();
            break;
        }
        /*.${SMs::Health::SM::global::alive::PILL_RESET} */
        case PILL_RESET_SIG: {
            status_ = Q_TRAN(&Health_simple);
            break;
        }
        default: {
            status_ = Q_SUPER(&Health_global);
            break;
        }
    }
    return status_;
}
/*.${SMs::Health::SM::global::alive::god} ..................................*/
QState Health_god(Health * const me, QEvt const * const e) {
    QState status_;
    switch (e->sig) {
        /*.${SMs::Health::SM::global::alive::god} */
        case Q_ENTRY_SIG: {
            #ifdef DESKTOP
            printf("Entered state god");
            #endif /* def DESKTOP */
            SetColor(WHITE);
            me->count=0;
            SaveState(GOD);
            status_ = Q_HANDLED();
            break;
        }
        /*.${SMs::Health::SM::global::alive::god} */
        case Q_EXIT_SIG: {
            #ifdef DESKTOP
            printf("Exited state god");
            #endif /* def DESKTOP */
            me->god_pause = GOD_PAUSE_M;
            status_ = Q_HANDLED();
            break;
        }
        /*.${SMs::Health::SM::global::alive::god::TIME_TICK_1S} */
        case TIME_TICK_1S_SIG: {
            /*.${SMs::Health::SM::global::alive::god::TIME_TICK_1S::[me->count>=GOD_THRESHOLD_S]} */
            if (me->count >= GOD_THRESHOLD_S) {
                status_ = Q_TRAN(&Health_god_ready);
            }
            /*.${SMs::Health::SM::global::alive::god::TIME_TICK_1S::[else]} */
            else {
                me->count++;
                status_ = Q_HANDLED();
            }
            break;
        }
        default: {
            status_ = Q_SUPER(&Health_alive);
            break;
        }
    }
    return status_;
}
/*.${SMs::Health::SM::global::alive::mortal} ...............................*/
QState Health_mortal(Health * const me, QEvt const * const e) {
    QState status_;
    switch (e->sig) {
        /*.${SMs::Health::SM::global::alive::mortal} */
        case Q_ENTRY_SIG: {
            #ifdef DESKTOP
            printf("Entered state mortal");
            #endif /* def DESKTOP */

            RAD_RECEIVED [else]
                SetHealth(me->health-e->damage);
                int red =  255*(1 - me->health/DEFAULT_HEALTH);
                int green = 255*me->health/DEFAULT_HEALTH
                ShowColor(red, green, 0);
                VibroRadiation();
                SaveHealth();
            status_ = Q_HANDLED();
            break;
        }
        /*.${SMs::Health::SM::global::alive::mortal} */
        case Q_EXIT_SIG: {
            #ifdef DESKTOP
            printf("Exited state mortal");
            #endif /* def DESKTOP */

            status_ = Q_HANDLED();
            break;
        }
        /*.${SMs::Health::SM::global::alive::mortal::RAD_RECEIVED} */
        case RAD_RECEIVED_SIG: {
            /*.${SMs::Health::SM::global::alive::mortal::RAD_RECEIVED::[me->health<=e->damage]} */
            if (me->health <= e->damage) {
                status_ = Q_TRAN(&Health_dead);
            }
            else {
                status_ = Q_UNHANDLED();
            }
            break;
        }
        /*.${SMs::Health::SM::global::alive::mortal::LONG_PRESS} */
        case LONG_PRESS_SIG: {
            status_ = Q_TRAN(&Health_dead);
            break;
        }
        default: {
            status_ = Q_SUPER(&Health_alive);
            break;
        }
    }
    return status_;
}
/*.${SMs::Health::SM::global::alive::mortal::god_ready} ....................*/
QState Health_god_ready(Health * const me, QEvt const * const e) {
    QState status_;
    switch (e->sig) {
        /*.${SMs::Health::SM::global::alive::mortal::god_ready} */
        case Q_ENTRY_SIG: {
            #ifdef DESKTOP
            printf("Entered state god_ready");
            #endif /* def DESKTOP */
            Flash(WHITE);
            SaveState(GOD_READY);
            SaveGodTimer();
            status_ = Q_HANDLED();
            break;
        }
        /*.${SMs::Health::SM::global::alive::mortal::god_ready} */
        case Q_EXIT_SIG: {
            #ifdef DESKTOP
            printf("Exited state god_ready");
            #endif /* def DESKTOP */

            status_ = Q_HANDLED();
            break;
        }
        /*.${SMs::Health::SM::global::alive::mortal::god_ready::TIME_TICK_1M} */
        case TIME_TICK_1M_SIG: {
            /*.${SMs::Health::SM::global::alive::mortal::god_ready::TIME_TICK_1M::[god_pause>0]} */
            if (god_pause > 0) {
                me->god_pause--;
                SaveGodTimer();
                status_ = Q_HANDLED();
            }
            else {
                status_ = Q_UNHANDLED();
            }
            break;
        }
        /*.${SMs::Health::SM::global::alive::mortal::god_ready::MIDDLE_BUTTON_PRESSED} */
        case MIDDLE_BUTTON_PRESSED_SIG: {
            /*.${SMs::Health::SM::global::alive::mortal::god_ready::MIDDLE_BUTTON_PR~::[me->god_pause==0]} */
            if (me->god_pause == 0) {
                status_ = Q_TRAN(&Health_god);
            }
            /*.${SMs::Health::SM::global::alive::mortal::god_ready::MIDDLE_BUTTON_PR~::[else]} */
            else {
                Flash(WHITE);
                status_ = Q_HANDLED();
            }
            break;
        }
        default: {
            status_ = Q_SUPER(&Health_mortal);
            break;
        }
    }
    return status_;
}
/*.${SMs::Health::SM::global::alive::mortal::simple} .......................*/
QState Health_simple(Health * const me, QEvt const * const e) {
    QState status_;
    switch (e->sig) {
        /*.${SMs::Health::SM::global::alive::mortal::simple} */
        case Q_ENTRY_SIG: {
            #ifdef DESKTOP
            printf("Entered state simple");
            #endif /* def DESKTOP */
            SaveState(SIMPLE);
            status_ = Q_HANDLED();
            break;
        }
        /*.${SMs::Health::SM::global::alive::mortal::simple} */
        case Q_EXIT_SIG: {
            #ifdef DESKTOP
            printf("Exited state simple");
            #endif /* def DESKTOP */

            status_ = Q_HANDLED();
            break;
        }
        /*.${SMs::Health::SM::global::alive::mortal::simple::PILL_GOD} */
        case PILL_GOD_SIG: {
            me->god_pause=0;
            status_ = Q_TRAN(&Health_god_ready);
            break;
        }
        default: {
            status_ = Q_SUPER(&Health_mortal);
            break;
        }
    }
    return status_;
}
/*.${SMs::Health::SM::global::dead} ........................................*/
QState Health_dead(Health * const me, QEvt const * const e) {
    QState status_;
    switch (e->sig) {
        /*.${SMs::Health::SM::global::dead} */
        case Q_ENTRY_SIG: {
            #ifdef DESKTOP
            printf("Entered state dead");
            #endif /* def DESKTOP */
            StopTransmit();
            SetHealth(0);
            VibroDeath();
            SaveState(DEAD);
            status_ = Q_HANDLED();
            break;
        }
        /*.${SMs::Health::SM::global::dead} */
        case Q_EXIT_SIG: {
            #ifdef DESKTOP
            printf("Exited state dead");
            #endif /* def DESKTOP */

            status_ = Q_HANDLED();
            break;
        }
        /*.${SMs::Health::SM::global::dead::PILL_RESET} */
        case PILL_RESET_SIG: {
            status_ = Q_TRAN(&Health_simple);
            break;
        }
        default: {
            status_ = Q_SUPER(&Health_global);
            break;
        }
    }
    return status_;
}

#ifdef DESKTOP
/*.${SMs::Health::SM::final} ...............................................*/
QState Health_final(Health * const me, QEvt const * const e) {
    QState status_;
    switch (e->sig) {
        /*.${SMs::Health::SM::final} */
        case Q_ENTRY_SIG: {
            printf("
            Bye! Bye!
            "); exit(0);
            status_ = Q_HANDLED();
            break;
        }
        default: {
            status_ = Q_SUPER(&QHsm_top);
            break;
        }
    }
    return status_;
}
#endif /* def DESKTOP */

/*.$enddef${SMs::Health} ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^*/


/*tranlated from diagrams code*/
