import asyncio

from extractor import PDFExtractor
from recognizer import IMGRecognizer

async def main():
    extractor = PDFExtractor()
    extractor.run()
    recognizer = IMGRecognizer()
    await recognizer.image_understanding()

if __name__ == '__main__':
    asyncio.run(main())