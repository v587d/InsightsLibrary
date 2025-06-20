import asyncio

from extractor import PDFExtractor
from recognizer import IMGRecognizer
from embedder import Embedder

async def main():
    ext = PDFExtractor()
    ext.run()
    rec = IMGRecognizer()
    await rec.image_understanding()

    # Ask user for confirmation to create text embeddings
    print("\n" + "=" * 60)
    print("Confirm if you need to create text vector embeddings")
    print("⚠️ This process may take approximately 20 minutes")
    print("=" * 60)

    while True:
        choice = input("Create embeddings? (Enter Y or N): ").strip().upper()
        if choice == 'Y':
            print("Starting text vector embedding creation, please wait...")
            em = Embedder()
            em.precalculation()
            print("Embedding creation completed!")
            break
        elif choice == 'N':
            print("Skipping embedding creation step")
            break
        else:
            print("Invalid input, please enter Y or N")

if __name__ == '__main__':
    asyncio.run(main())
