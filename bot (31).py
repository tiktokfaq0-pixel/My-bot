import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import zipfile
import re
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO"),
)
log = logging.getLogger("office-pdf-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "20"))
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".docx", ".doc", ".rtf", ".odt",
    ".xlsx", ".xls", ".csv", ".ods",
    ".pptx", ".ppt", ".ppsx", ".pps", ".odp",
    ".txt", ".html", ".htm",
}


def convert_to_pdf(source: Path, output_dir: Path) -> Path:
    """Convert an Office/OpenDocument file to PDF using LibreOffice."""
    profile = output_dir / "lo-profile"
    profile.mkdir(exist_ok=True)
    command = [
        "libreoffice",
        "--headless",
        f"-env:UserInstallation=file://{profile}",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(source),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "LibreOffice conversion failed")
    expected = output_dir / f"{source.stem}.pdf"
    if expected.exists():
        return expected
    candidates = sorted(output_dir.glob("*.pdf"))
    if not candidates:
        raise RuntimeError("PDF was not created")
    return candidates[0]


def normalize_pyidaungsu(source: Path) -> None:
    """Force embedded OOXML font declarations to Pyidaungsu for stable Myanmar rendering."""
    if source.suffix.lower() not in {".docx", ".xlsx", ".pptx", ".docm", ".xlsm", ".pptm", ".odt", ".ods", ".odp"}:
        return
    temp = source.with_suffix(source.suffix + ".fontfix")
    try:
        with zipfile.ZipFile(source, "r") as zin, zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.endswith(".xml"):
                    text = data.decode("utf-8", errors="replace")
                    # Word font declarations.
                    text = re.sub(r"(w:(?:ascii|hAnsi|eastAsia|cs)=\")[^\" ]*(\")", r"\1Pyidaungsu\2", text)
                    # Excel font declarations.
                    text = re.sub(r'(<name\b[^>]*\bval=")[^"]*(")', r'\1Pyidaungsu\2', text)
                    # PowerPoint DrawingML font declarations.
                    text = re.sub(r'((?:latin|ea|cs)\b[^>]*\btypeface=")[^"]*(")', r'\1Pyidaungsu\2', text)
                    data = text.encode("utf-8")
                zout.writestr(item, data)
        temp.replace(source)
    finally:
        if temp.exists():
            temp.unlink(missing_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "မင်္ဂလာပါ။ DOCX/XLSX ဖိုင်ပို့ပါ။ PDF အဖြစ်ပြောင်းပြီး ပြန်ပို့ပေးပါမယ်။\n\n"
        "လက်ခံသောဖိုင်များ: Word, Excel, PowerPoint, OpenDocument, RTF, CSV, TXT, HTML\n"
        f"ဖိုင်အရွယ်အစားအများဆုံး: {MAX_FILE_MB} MB"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    document = message.document
    original_name = document.file_name or "document"
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        await message.reply_text("ဒီဖိုင်အမျိုးအစားကို မထောက်ပံ့သေးပါ။ Word, Excel, PowerPoint သို့မဟုတ် OpenDocument ဖိုင်ပို့ပါ။")
        return
    if document.file_size and document.file_size > MAX_FILE_BYTES:
        await message.reply_text(f"ဖိုင်အရွယ်အစား {MAX_FILE_MB} MB ထက် မကျော်ရပါ။")
        return

    await message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
    status = await message.reply_text("ဖိုင်ကို PDF ပြောင်းနေပါတယ်…")
    work_dir = Path(tempfile.mkdtemp(prefix="tg-office-pdf-"))
    try:
        safe_name = Path(original_name).name.replace("/", "_").replace("\\", "_")
        source = work_dir / safe_name
        tg_file = await document.get_file(
            read_timeout=600, write_timeout=600, connect_timeout=60, pool_timeout=60
        )
        await tg_file.download_to_drive(
            custom_path=str(source),
            read_timeout=600, write_timeout=600, connect_timeout=60, pool_timeout=60
        )
        normalize_pyidaungsu(source)
        pdf_path = await asyncio.to_thread(convert_to_pdf, source, work_dir)
        await status.edit_text("ပြီးပါပြီ။ PDF ဖိုင်ကို ပို့နေပါတယ်…")
        with pdf_path.open("rb") as pdf_file:
            await message.reply_document(
                document=pdf_file,
                filename=f"{source.stem}.pdf",
                caption="PDF ပြောင်းပြီးပါပြီ။",
                read_timeout=600, write_timeout=600, connect_timeout=60, pool_timeout=60,
            )
        await status.delete()
    except Exception as exc:
        log.exception("Conversion failed for %s", original_name)
        detail = str(exc).lower()
        if "too big" in detail or "file is too large" in detail or "entity too large" in detail:
            msg = "ဒီဖိုင်က Telegram Bot ရဲ့ 20 MB download limit ထက် ကြီးနေပါတယ်။ ဖိုင်ကို 20 MB အောက်ချုံ့ပြီး ပြန်ပို့ပါ။"
        elif "timeout" in detail or "timed out" in detail:
            msg = "ဖိုင်ကြီးလို့ download/conversion timeout ဖြစ်သွားပါတယ်။ ဖိုင်ကို ခွဲပို့ပါ သို့မဟုတ် အရွယ်အစားလျှော့ပြီး ပြန်ပို့ပါ။"
        else:
            msg = "PDF ပြောင်းရာမှာ အမှားတစ်ခုဖြစ်သွားပါတယ်။ ဖိုင်ကို ပြန်ပို့ကြည့်ပါ။ ဖိုင် 20 MB အောက်ဖြစ်ကြောင်းလည်း စစ်ပါ။"
        await status.edit_text(msg)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("PDF ပြောင်းရန် Office/OpenDocument ဖိုင်ကို document အဖြစ် ပို့ပါ။")


def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is missing. Copy .env.example to .env and set your Telegram bot token.")
    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(~filters.COMMAND, handle_other))
    log.info("Bot is running")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
