# Полный список товаров с командами для сервера
PRIVILEGES = {
    "VIP": {
        "type": "period",
        "price": {"month": 85, "forever": 220},
        "cmd": {
            "month": "oxide.usergroup add {steam_id} vip 30d",
            "forever": "oxide.usergroup add {steam_id} vip"
        }
    },
    "PREMIUM": {
        "type": "period",
        "price": {"month": 120, "forever": 250},
        "cmd": {
            "month": "oxide.usergroup add {steam_id} PREMIUM 30d",
            "forever": "oxide.usergroup add {steam_id} PREMIUM"
        }
    },
    "DELUXE": {
        "type": "period",
        "price": {"month": 150, "forever": 300},
        "cmd": {
            "month": "oxide.usergroup add {steam_id} DELUXE 30d",
            "forever": "oxide.usergroup add {steam_id} DELUXE"
        }
    },
    "ELITE": {
        "type": "period",
        "price": {"month": 200, "forever": 350},
        "cmd": {
            "month": "oxide.usergroup add {steam_id} ELITE 30d",
            "forever": "oxide.usergroup add {steam_id} ELITE"
        }
    },
    "CEZAR": {
        "type": "period",
        "price": {"month": 250, "forever": 400},
        "cmd": {
            "month": "oxide.usergroup add {steam_id} CEZAR 30d",
            "forever": "oxide.usergroup add {steam_id} CEZAR"
        }
    },
    "Доп ХП": {
        "type": "level",
        "price_per_level": 25,
        "cmd": "bhealthi {steam_id} {level}",
        "description": "✦ Каждый раз при покупке и активации данного товара вы будете получать +100 доп. HP.\n\nМаксимум можно приобрести 20 000 HP.\n\n⚙ Примеры команд переключения между HP:\n/hp 500   /hp 1500   /hp 9800"
    },
    "Доп урон": {
        "type": "level",
        "price_per_level": 25,
        "cmd": "wpdamagei {steam_id} {level}",
        "description": "✦ Каждый раз при покупке данного товара вы будете получать одну единицу доп. урона.\n\nМаксимум можно купить X200 урона.\n\n⚙ Примеры чат-команд для переключения урона:\n/damage 3   /damage 33   /damage 77"
    },
    "Регенерация": {
        "type": "level",
        "price_per_level": 25,
        "cmd": "hticki {steam_id} {level}",
        "description": "✦ Каждый раз при покупке данного товара вы будете получать одну единицу регенерации в секунду.\n\nМаксимум можно приобрести 200 единиц регенерации в секунду.\n\n⚙ Примеры команд для переключения уровня регенерации:\n/regen set 5   /regen set 55   /regen set 98"
    },
    "SPONSOR": {
        "type": "sponsor",
        "price_per_level": 1500,
        "max_level": 21,
        "cmd": "oxide.usergroup add {steam_id} sponsor{level:03d}"
    },
    "Телепорт по карте": {
        "type": "simple",
        "price": 500,
        "cmd": "oxide.usergroup add {steam_id} tpkarta"
    },
    "Бесконечные патроны": {
        "type": "simple",
        "price": 500,
        "cmd": "oxide.usergroup add {steam_id} ammo"
    },
    "Radar": {
        "type": "simple",
        "price": 500,
        "cmd": "radar.givelevel {steam_id} 1"
    },
    "Кастомный набор (3 кита)": {
        "type": "simple",
        "price": 2500,
        "cmd": "Свяжитесь с администратором для создания наборов"
    },
    "Набор Локи": {
        "type": "simple",
        "price": 250,
        "cmd": "oxide.usergroup add {steam_id} Loki"
    },
    "Набор Тор": {
        "type": "simple",
        "price": 350,
        "cmd": "oxide.usergroup add {steam_id} Top"
    },
    "Набор Зевс": {
        "type": "simple",
        "price": 450,
        "cmd": "oxide.usergroup add {steam_id} ZEVS"
    },
    "UberTool": {
        "type": "simple",
        "price": 2500,
        "cmd": "oxide.usergroup add {steam_id} UberTool"
    },
    "Волшебный рюкзак": {
        "type": "simple",
        "price": 400,
        "cmd": "oxide.usergroup add {steam_id} SOSWIPE"
    },
    "Черная винтовка (7 дней)": {
        "type": "simple",
        "price": 120,
        "cmd": "oxide.usergroup add {steam_id} L96 7d\nw_give {steam_id} 30 30"
    },
    "Игнор черной винтовки (30 дней)": {
        "type": "simple",
        "price": 250,
        "cmd": "oxide.usergroup add {steam_id} L96ignore 30d"
    },
    "King": {
        "type": "simple",
        "price": 25000,
        "cmd": "oxide.usergroup add {steam_id} KING 30d"
    }
}

async def fetch_prices():
    return PRIVILEGES