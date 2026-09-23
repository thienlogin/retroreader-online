# RetroReader Online Library

Kho truyện online cho ứng dụng **RetroReader** trên TrimUI Brick Pro.

## Cấu trúc thư mục

```
manga/           ← Truyện tranh (.cbz, .cbr, .pdf)
novels/          ← Truyện chữ / Ebook (.epub, .mobi, .pdf)  
audiobooks/      ← Sách nói (.mp3)
catalog.json     ← Index tất cả nội dung
```

## Cách sử dụng

1. Upload file truyện/sách/audio vào đúng thư mục
2. Chạy script `generate_catalog.py` để cập nhật `catalog.json`
3. Push lên GitHub
4. RetroReader sẽ tự fetch catalog và hiển thị

## Định dạng hỗ trợ

| Loại | Định dạng | Thư mục |
|---|---|---|
| Truyện tranh | `.cbz`, `.cbr`, `.pdf` | `manga/` |
| Truyện chữ | `.epub`, `.mobi`, `.azw3`, `.pdf` | `novels/` |
| Sách nói | `.mp3`, `.m4a`, `.m4b` | `audiobooks/` |
