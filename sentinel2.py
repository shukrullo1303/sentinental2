import datetime

import ee
import geemap


def initialize_ee(project_id: str) -> None:
    """Google Earth Engine-ni xavfsiz ishga tushirish."""
    try:
        ee.Initialize(project=project_id)
    except Exception:
        print(
            "Avtorizatsiya talab qilinadi. Iltimos, terminalda "
            "'earthengine authenticate' buyrug'ini bering."
        )
        ee.Authenticate()
        ee.Initialize(project=project_id)


def main() -> None:
    project_id = "rounded-elf-1303"

    # 1. Google Earth Engine-ni ishga tushirish
    initialize_ee(project_id)
    print("Tizim ishga tushdi. Ma'lumotlar yuklanmoqda...")

    # 2. Hududni belgilash (Asaka tumani koordinatalari)
    # Asaka tumani markazi: 72.23, 40.64
    asaka_point = ee.Geometry.Point([72.23, 40.64])

    # 3. Vaqt oralig'ini avtomatik aniqlash (Bugungi kundan oldingi 30 kun)
    today = datetime.date.today()
    past_date = today - datetime.timedelta(days=60)
    date_start = past_date.strftime("%Y-%m-%d")
    date_end = today.strftime("%Y-%m-%d")

    print(f"{date_start} dan {date_end} gacha bo'lgan tasvirlar qidirilmoqda...")

    # 4. Sentinel-2 kolleksiyasini chaqirish va filtrlash (harmonized versiyasi)
    #  Avval 10% dan kam bulutli rasmlarni qidiramiz, so'ng bosqichma-bosqich
    #  cheklovni yumshatamiz.
    base_collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(asaka_point)
        .filterDate(date_start, date_end)
    )

    # 10% gacha bulutli rasmlar
    collection = base_collection.filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 10))
    image_count = collection.size().getInfo()

    if image_count == 0:
        print(
            "10% gacha bulutli rasmlar topilmadi. "
            "Bulut foizini 40% gacha oshirib qidiryapmiz..."
        )
        collection = base_collection.filter(
            ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40)
        )
        image_count = collection.size().getInfo()

    if image_count == 0:
        print(
            "Hali ham rasm topilmadi. Bulut cheklovisiz barcha tasvirlarni "
            "qidiryapmiz..."
        )
        collection = base_collection
        image_count = collection.size().getInfo()

    # Kolleksiya hajmini yakuniy tekshirish
    if image_count == 0:
        print(
            "Haqiqatan ham tanlangan davr uchun Sentinel-2 tasvirlari topilmadi. "
            "Vaqt oralig'ini yana kengaytirib ko'ring."
        )
        return

    print(f"Topilgan tasvirlar soni: {image_count}")

    # Eng kam bulutli tasvirni tanlash
    dataset = collection.sort("CLOUDY_PIXEL_PERCENTAGE").first()

    # 5. NDVI (O'simlik indeksi) ni hisoblash
    ndvi = dataset.normalizedDifference(["B8", "B4"]).rename("NDVI")

    # 6. Vizualizatsiya parametrlari
    vis_params = {
        "min": 0.0,
        "max": 0.8,
        "palette": [
            "FFFFFF",  # Oq - Qor yoki bulut
            "CE7E45",  # Jigarrang - Tuproq/Cho'l (O'simlik yo'q)
            "DF923D",  # Och jigarrang - Siyrak o'simlik
            "F1B555",  # Sariq - Quriyotgan o'tlar
            "FCD163",
            "99B718",  # Och yashil - Ekinlar
            "74A901",
            "66A000",
            "529400",
            "3E8601",
            "207401",
            "056201",
            "004C00",  # To'q yashil - Qalin o'rmon/Sog'lom ekin
            "023B01",
            "012E01",
            "011D01",
            "011301",
        ],
    }

    # 7. Xaritani yaratish va saqlash
    Map = geemap.Map()
    Map.centerObject(asaka_point, 12)  # 12 - masshtab (zoom level)

    # Asl sun'iy yo'ldosh tasvirini qo'shish
    Map.addLayer(
        dataset,
        {"min": 0, "max": 3000, "bands": ["B4", "B3", "B2"]},
        "Haqiqiy Rang (RGB)",
    )

    # NDVI qatlamini qo'shish
    Map.addLayer(ndvi, vis_params, "NDVI (O'simlik salomatligi)")

    # Ranglar shkalasini qo'shish
    Map.add_colorbar(
        vis_params,
        label="NDVI Indeksi (0=Tuproq, 1=Qalin o'simlik)",
    )

    # Xaritani HTML faylga saqlash
    output_file = "asaka_monitor.html"
    Map.save(output_file)

    print(f"Muvaffaqiyatli yakunlandi! '{output_file}' faylini ochib ko'ring.")


if __name__ == "__main__":
    main()
