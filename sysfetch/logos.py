"""Built-in logo art, taken from fastfetch's Windows/ASCII logo set.

Each entry stores the raw art with ``$N`` colour placeholders exactly as
fastfetch writes it, plus the colour list / key colour / title colour that
the matching logo definition uses.
"""

from __future__ import annotations

LOGOS: dict[str, dict] = {
    'windows_11': {
        "art": '$1/////////////////  $2/////////////////\n$1/////////////////  $2/////////////////\n$1/////////////////  $2/////////////////\n$1/////////////////  $2/////////////////\n$1/////////////////  $2/////////////////\n$1/////////////////  $2/////////////////\n$1/////////////////  $2/////////////////\n$1/////////////////  $2/////////////////\n\n$3/////////////////  $4/////////////////\n$3/////////////////  $4/////////////////\n$3/////////////////  $4/////////////////\n$3/////////////////  $4/////////////////\n$3/////////////////  $4/////////////////\n$3/////////////////  $4/////////////////\n$3/////////////////  $4/////////////////\n$3/////////////////  $4/////////////////',
        "colors": ['34', '34', '34', '34'],
        "colorKeys": '33',
        "colorTitle": '36',
        "names": ['Windows 11', 'Windows Server 2022'],
    },
    'windows': {
        "art": '$1        ,.=:!!t3Z3z.,\n       :tt:::tt333EE3\n$1       Et:::ztt33EEEL$2 @Ee.,      ..,\n$1      ;tt:::tt333EE7$2 ;EEEEEEttttt33#\n$1     :Et:::zt333EEQ.$2 $EEEEEttttt33QL\n$1     it::::tt333EEF$2 @EEEEEEttttt33F\n$1    ;3=*^```"*4EEV$2 :EEEEEEttttt33@.\n$3    ,.=::::!t=., $1`$2 @EEEEEEtttz33QF\n$3   ;::::::::zt33)$2   "4EEEtttji3P*\n$3  :t::::::::tt33.$4:Z3z..$2  ``$4 ,..g.\n$3  i::::::::zt33F$4 AEEEtttt::::ztF\n$3 ;:::::::::t33V$4 ;EEEttttt::::t3\n$3 E::::::::zt33L$4 @EEEtttt::::z3F\n$3{3=*^```"*4E3)$4 ;EEEtttt:::::tZ`\n$3             `$4 :EEEEtttt::::z7\n                 "VEzjt:;;z>*`',
        "colors": ['31', '32', '33', '34'],
        "colorKeys": '34',
        "colorTitle": '32',
        "names": ['Windows', 'Windows 7', 'Windows Server 2008', 'Windows Server 2008 R2'],
    },
    'linux': {
        "art": '        $2#####\n       $2#######\n       $2##$1O$2#$1O$2##\n       $2#$3#####$2#\n     $2##$1##$3###$1##$2##\n    $2#$1##########$2##\n   $2#$1############$2##\n   $2#$1############$2###\n  $3##$2#$1###########$2##$3#\n$3######$2#$1#######$2#$3######\n$3#######$2#$1#####$2#$3#######\n  $3#####$2#######$3#####',
        "colors": ['37', '90', '33'],
        "colorKeys": '',
        "colorTitle": '33',
        "names": ['Linux', 'linux-generic'],
    },
    'macos': {
        "art": '                     ..\'\n                 ,xNMM.\n               .OMMMMo\n               lMM"\n     .;loddo:.  .olloddol;.\n   cKMMMMMMMMMMNWMMMMMMMMMM0:\n $2.KMMMMMMMMMMMMMMMMMMMMMMMWd.\n XMMMMMMMMMMMMMMMMMMMMMMMX.\n$3;MMMMMMMMMMMMMMMMMMMMMMMM:\n:MMMMMMMMMMMMMMMMMMMMMMMM:\n$4.MMMMMMMMMMMMMMMMMMMMMMMMX.\n kMMMMMMMMMMMMMMMMMMMMMMMMWd.\n $5\'XMMMMMMMMMMMMMMMMMMMMMMMMMMk\n  \'XMMMMMMMMMMMMMMMMMMMMMMMMK.\n    $6kMMMMMMMMMMMMMMMMMMMMMMd\n     ;KMMMMMMMWXXWMMMMMMMk.\n       "cooc*"    "*coo\'"',
        "colors": ['32', '33', '91', '31', '35', '34'],
        "colorKeys": '33',
        "colorTitle": '32',
        "names": ['macOS'],
    },
    'ubuntu': {
        "art": "                             ....\n              $2.',:clooo:  $1.:looooo:.\n           $2.;looooooooc  $1.oooooooooo'\n        $2.;looooool:,''.  $1:ooooooooooc\n       $2;looool;.         $1'oooooooooo,\n      $2;clool'             $1.cooooooc.  $2,,\n         $2...                $1......  $2.:oo,\n  $1.;clol:,.                        $2.loooo'\n $1:ooooooooo,                        $2'ooool\n$1'ooooooooooo.                        $2loooo.\n$1'ooooooooool                         $2coooo.\n $1,loooooooc.                        $2.loooo.\n   $1.,;;;'.                          $2;ooooc\n       $2...                         $2,ooool.\n    $2.cooooc.              $1..',,'.  $2.cooo.\n      $2;ooooo:.           $1;oooooooc.  $2:l.\n       $2.coooooc,..      $1coooooooooo.\n         $2.:ooooooolc:. $1.ooooooooooo'\n           $2.':loooooo;  $1,oooooooooc\n               $2..';::c'  $1.;loooo:'",
        "colors": ['31', '31'],
        "colorKeys": '',
        "colorTitle": '',
        "names": ['ubuntu'],
    },
}


def resolve(name: str) -> str | None:
    """Map a user supplied logo name to a built-in logo key (case-insensitive)."""
    lowered = name.strip().lower()
    if lowered in LOGOS:
        return lowered
    for key, logo in LOGOS.items():
        for alias in logo["names"]:
            if alias.lower() == lowered:
                return key
    return None
