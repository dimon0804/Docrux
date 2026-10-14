/**
 * Запись короткого вопроса с микрофона в WAV 16 кГц, моно, 16 бит.
 *
 * Сервер распознаёт речь локальной моделью и ждёт именно такой формат, поэтому
 * звук приводится к нему прямо в браузере: без сжатых форматов и без ffmpeg.
 */

const RATE = 16000;
export const MAX_SECONDS = 15;

export type Recording = { stop: () => Promise<Blob>; cancel: () => void };

function downsample(input: Float32Array, from: number): Int16Array {
  const ratio = from / RATE;
  const length = Math.floor(input.length / ratio);
  const out = new Int16Array(length);
  for (let index = 0; index < length; index += 1) {
    // Среднее по окну: простое сглаживание перед прореживанием.
    const start = Math.floor(index * ratio);
    const end = Math.min(Math.floor((index + 1) * ratio), input.length);
    let sum = 0;
    for (let k = start; k < end; k += 1) sum += input[k]!;
    const value = Math.max(-1, Math.min(1, sum / Math.max(end - start, 1)));
    out[index] = value < 0 ? value * 0x8000 : value * 0x7fff;
  }
  return out;
}

function wav(samples: Int16Array): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const text = (offset: number, value: string) => {
    for (let i = 0; i < value.length; i += 1) view.setUint8(offset + i, value.charCodeAt(i));
  };
  text(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  text(8, "WAVE");
  text(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, RATE, true);
  view.setUint32(28, RATE * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  text(36, "data");
  view.setUint32(40, samples.length * 2, true);
  new Int16Array(buffer, 44).set(samples);
  return new Blob([buffer], { type: "audio/wav" });
}

export async function startRecording(onLimit: () => void): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
  });
  const context = new AudioContext();
  const source = context.createMediaStreamSource(stream);
  // ScriptProcessor устарел, но работает везде и не требует отдельного файла воркера,
  // который запретила бы политика безопасности страницы.
  const processor = context.createScriptProcessor(4096, 1, 1);
  const chunks: Float32Array[] = [];
  let length = 0;
  processor.onaudioprocess = (event) => {
    const data = new Float32Array(event.inputBuffer.getChannelData(0));
    chunks.push(data);
    length += data.length;
    if (length / context.sampleRate >= MAX_SECONDS) onLimit();
  };
  source.connect(processor);
  processor.connect(context.destination);

  const release = () => {
    processor.disconnect();
    source.disconnect();
    stream.getTracks().forEach((track) => track.stop());
    void context.close();
  };

  return {
    stop: async () => {
      release();
      const joined = new Float32Array(length);
      let offset = 0;
      for (const chunk of chunks) {
        joined.set(chunk, offset);
        offset += chunk.length;
      }
      return wav(downsample(joined, context.sampleRate));
    },
    cancel: release,
  };
}
