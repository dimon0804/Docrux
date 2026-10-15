"""Командная строка: разбор одного файла, пакетный прогон набора и Telegram-бот."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from docrux.batch import run_batch
from docrux.pipeline import Pipeline
from docrux.settings import Settings

app = typer.Typer(add_completion=False, help="Докрукс: цифровой секретарь деканата.")


def _pipeline(text_layer: bool) -> Pipeline:
    settings = Settings(pdf_text_layer="prefer" if text_layer else "ignore")
    return Pipeline.default(settings)


@app.command()
def batch(
    manifest: Annotated[Path, typer.Argument(help="documents.json из набора данных")],
    questions: Annotated[Path | None, typer.Option(help="questions.json")] = None,
    out: Annotated[Path, typer.Option(help="куда сохранить результат")] = Path("results.json"),
    source: Annotated[str, typer.Option(help="image или pdf")] = "image",
    text_layer: Annotated[
        bool, typer.Option(help="брать текстовый слой PDF вместо распознавания")
    ] = False,
) -> None:
    """Обрабатывает все документы набора и сохраняет results.json."""
    if questions is None and (manifest.parent / "questions.json").exists():
        questions = manifest.parent / "questions.json"
    result = run_batch(
        _pipeline(text_layer),
        manifest,
        questions,
        source,
        progress=lambda name: typer.echo(f"  {name}", err=True),
    )
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    typer.echo(f"Готово: {len(result['documents'])} документов -> {out}")


@app.command()
def read(
    file: Annotated[Path, typer.Argument(help="JPG, PNG или PDF")],
    doc_type: Annotated[str | None, typer.Option("--type", help="тип документа")] = None,
    question: Annotated[str | None, typer.Option("-q", "--question")] = None,
    text_layer: Annotated[bool, typer.Option()] = False,
) -> None:
    """Разбирает один документ: текст, карточка, проверка и ответ на вопрос."""
    pipeline = _pipeline(text_layer)
    analysis = pipeline.analyze(file.read_bytes(), doc_type).analysis
    typer.echo(f"Тип: {analysis.document_title}")
    for field in analysis.fields:
        typer.echo(f"  {field.label}: {field.value}")
    typer.echo(pipeline.check(analysis).answer)
    if question:
        answer = pipeline.ask(analysis, question)
        typer.echo(
            f"\n{question}\n{answer.answer}\nИсточники: {', '.join(answer.sources) or 'нет'}"
        )


@app.command()
def types() -> None:
    """Показывает подключённые типы документов."""
    for doc_type in _pipeline(False).registry:
        typer.echo(f"{doc_type.id}: {doc_type.title} ({len(doc_type.fields)} полей)")


@app.command()
def bot() -> None:
    """Запускает Telegram-бота. Токен берётся из DOCRUX_BOT_TOKEN."""
    try:
        from docrux.bot.app import BotTokenMissing, main
    except ImportError:
        typer.echo('Для бота нужен aiogram: pip install ".[bot]"', err=True)
        raise typer.Exit(2) from None
    try:
        main()
    except BotTokenMissing as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from None
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    app()
