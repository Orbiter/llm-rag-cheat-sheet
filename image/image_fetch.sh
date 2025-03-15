#!/bin/bash

mkdir -p images

urls=(
    "https://upload.wikimedia.org/wikipedia/commons/e/e7/Everest_North_Face_toward_Base_Camp_Tibet_Luca_Galuzzi_2006.jpg"
    "https://upload.wikimedia.org/wikipedia/commons/5/56/USA-Stamp-1973-ZIPCode.jpg"
    "https://upload.wikimedia.org/wikipedia/commons/a/a8/Picture_of_fruit_and_vegetables.jpg"
    "https://upload.wikimedia.org/wikipedia/commons/c/c1/Wikipedia_Logo_as_ASCII_Art_recompress.png"
    "https://upload.wikimedia.org/wikipedia/commons/a/a3/June_odd-eyed-cat.jpg"
    "https://upload.wikimedia.org/wikipedia/commons/f/f8/Wikipedia_editor_hat_w_dog.JPG"
    "https://upload.wikimedia.org/wikipedia/en/b/be/Disloyal_man_with_his_girlfriend_looking_at_another_girl.jpg"
    "https://upload.wikimedia.org/wikipedia/commons/0/06/ElectricBlender.jpg"
    "https://upload.wikimedia.org/wikipedia/en/e/ed/Nyan_cat_250px_frame.PNG"
    "https://upload.wikimedia.org/wikipedia/en/f/fd/Pusheen_the_Cat.png"
    "https://upload.wikimedia.org/wikipedia/commons/d/df/202406111126_IMG_1268.jpg"
    "https://upload.wikimedia.org/wikipedia/commons/6/6f/Mychtar_and_his_Snowdog.jpg"
    "https://upload.wikimedia.org/wikipedia/commons/2/28/Commodore64withdisk.jpg"
    "https://upload.wikimedia.org/wikipedia/commons/0/02/Minecraft_Wiki_2023_textless.png"
    "https://upload.wikimedia.org/wikipedia/en/d/de/Doom_ingame_1.png"
)

for url in "${urls[@]}"; do
    filename=$(basename "$url")
    if [ ! -f "images/$filename" ]; then
        wget -P images "$url"
    else
        echo "images/$filename already exists, skipping download."
    fi
done
