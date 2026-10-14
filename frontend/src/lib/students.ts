/**
 * Сверка документов в пакете по студентам: у кого какие документы и где ФИО
 * пишется почти одинаково, но не совпадает. «Захаров Фёдор Дмитриевич» и
 * «Захарова Фёдор Дмитриевич» — скорее всего, опечатка в одном из документов.
 */

export type StudentDoc = { file: string; title: string; name: string };
export type Student = { name: string; docs: StudentDoc[]; similar: string[] };

const norm = (name: string) => name.toLowerCase().replace(/ё/g, "е").replace(/\s+/g, " ").trim();

function distance(a: string, b: string): number {
  const row = Array.from({ length: b.length + 1 }, (_, index) => index);
  for (let i = 1; i <= a.length; i += 1) {
    let previous = row[0]!;
    row[0] = i;
    for (let j = 1; j <= b.length; j += 1) {
      const saved = row[j]!;
      row[j] = Math.min(row[j]! + 1, row[j - 1]! + 1, previous + (a[i - 1] === b[j - 1] ? 0 : 1));
      previous = saved;
    }
  }
  return row[b.length]!;
}

/** «Захаров Ф. Д.» совпадает с «Захаров Фёдор Дмитриевич» по фамилии и инициалам. */
function sameByInitials(a: string, b: string) {
  const [sa, ...ra] = a.split(" ");
  const [sb, ...rb] = b.split(" ");
  if (sa !== sb || ra.length !== rb.length) return false;
  return ra.every((part, index) => part.charAt(0) === rb[index]!.charAt(0));
}

export function groupStudents(docs: StudentDoc[]): Student[] {
  const groups = new Map<string, Student>();
  for (const doc of docs) {
    const key = norm(doc.name);
    const group = groups.get(key) ?? { name: doc.name, docs: [], similar: [] };
    group.docs.push(doc);
    groups.set(key, group);
  }
  const keys = [...groups.keys()];
  for (let i = 0; i < keys.length; i += 1) {
    for (let j = i + 1; j < keys.length; j += 1) {
      const a = keys[i]!;
      const b = keys[j]!;
      if (distance(a, b) <= 2 || sameByInitials(a, b)) {
        groups.get(a)!.similar.push(groups.get(b)!.name);
        groups.get(b)!.similar.push(groups.get(a)!.name);
      }
    }
  }
  return [...groups.values()].sort(
    (x, y) => y.docs.length - x.docs.length || x.name.localeCompare(y.name, "ru"),
  );
}
