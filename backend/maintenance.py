"""Offline maintenance commands. Stop the application before migration/restore."""
import argparse
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import shutil

from dotenv import load_dotenv
from catalog_manager import cargar_catalogos
from storage import Store

ROOT = Path(__file__).resolve().parent.parent


def main():
    load_dotenv(ROOT / '.env')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', default=os.getenv('CONSULTORIO_DATA_DIR', str(ROOT / 'data')))
    parser.add_argument('--tickets-dir', default=os.getenv('CONSULTORIO_TICKETS_DIR', str(ROOT / 'Tickets')))
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('migrate')
    commands.add_parser('verify')
    backup = commands.add_parser('backup')
    backup.add_argument('--output', required=True, help='Carpeta nueva, preferentemente en otra unidad')
    restore = commands.add_parser('restore')
    restore.add_argument('--source', required=True, help='Respaldo que contiene BACKUP_COMPLETE')
    restore.add_argument('--output', required=True, help='Directorio nuevo para restaurar sin sobrescribir datos')
    args = parser.parse_args()
    store = Store(args.data_dir, args.tickets_dir)
    if args.command == 'restore':
        source, destination = Path(args.source).resolve(), Path(args.output).resolve()
        if not (source / 'BACKUP_COMPLETE').is_file() or destination.exists() or destination.is_relative_to(source):
            parser.exit(1, 'Seleccione un respaldo completo y un directorio nuevo fuera de él.\n')
        with closing(sqlite3.connect((source / 'consultorio.sqlite3').as_uri() + '?mode=ro', uri=True)) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or db.execute('PRAGMA foreign_key_check').fetchall():
                parser.exit(1, 'El respaldo no pasó la comprobación de integridad.\n')
        shutil.copytree(source, destination)
        with closing(sqlite3.connect(destination / 'consultorio.sqlite3')) as db:
            db.execute("UPDATE jobs SET state='uncertain',error='Respaldo restaurado: verifique el papel antes de reimprimir.' WHERE kind='print' AND state IN ('pending','running')")
            db.execute("UPDATE jobs SET state='pending' WHERE kind!='print' AND state='running'")
            db.commit()
        print('Restaurado en:', destination)
        print('Configure CONSULTORIO_DATA_DIR y CONSULTORIO_TICKETS_DIR para utilizar esta copia.')
    elif args.command == 'verify':
        if not store.path.is_file():
            parser.exit(1, 'La base todavía no existe.\n')
        with closing(sqlite3.connect(store.path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
            integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
            foreign_keys = db.execute('PRAGMA foreign_key_check').fetchall()
            count = db.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
        if integrity != 'ok' or foreign_keys:
            parser.exit(1, 'La base no pasó la comprobación de integridad.\n')
        print(f'Integridad correcta. Tickets: {count}.')
    else:
        cargar_catalogos(args.data_dir)
        store.initialize(recover_jobs=args.command == 'migrate')
        if args.command == 'backup':
            print('Respaldo verificado:', store.backup(args.output))
        else:
            print('Migración completada. Los archivos heredados se conservaron.')


if __name__ == '__main__':
    main()
