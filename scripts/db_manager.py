# scripts/db_manager.py
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import configparser
import os

def _resolve_config_path(config_path: Optional[str|os.PathLike]=None) -> Path:
    if config_path:
        p = Path(config_path).expanduser().resolve()
        if p.exists():
            return p
        raise FileNotFoundError(f"config.ini non trovato: {p}")
    for candidate in [Path.cwd()/ "config.ini", Path(__file__).resolve().parents[1]/"config.ini"]:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Impossibile trovare config.ini")

def _read_config(config_path: Optional[str|os.PathLike]=None) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    file = _resolve_config_path(config_path)
    cfg.read(file, encoding="utf-8")
    return cfg

def get_connection(config_path: Optional[str|os.PathLike]=None) -> sqlite3.Connection:
    cfg = _read_config(config_path)
    db_path_str = cfg["Autenticazione"]["percorso_database"]
    
    # Gestisci percorsi cross-platform
    db_path = Path(db_path_str).expanduser()
    
    # Se il percorso è relativo, risolvilo rispetto alla root del progetto
    if not db_path.is_absolute():
        project_root = Path(__file__).resolve().parents[1]
        db_path = project_root / db_path
    
    db_path = db_path.resolve()
    
    # Crea la directory se non esiste
    db_dir = db_path.parent
    if not db_dir.exists():
        db_dir.mkdir(parents=True, exist_ok=True)
    
    # Connetti al database (SQLite lo crea automaticamente se non esiste)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

# ---- Documenti ----
DOC_SELECT = """
SELECT d.id AS documento_id, d.tipo_documento, d.numero_documento, d.data_documento, d.importo_totale,
       s.id AS scadenza_id, s.data_scadenza, s.importo_scadenza,
       sg.id AS soggetto_id, sg.ragione_sociale
FROM Documenti d
LEFT JOIN Scadenze s ON s.documento_id = d.id
LEFT JOIN Soggetti sg ON sg.id = d.soggetto_id
"""

def fetch_documents(conn: sqlite3.Connection, soggetto_id: Optional[int]=None, limit: Optional[int]=200) -> List[sqlite3.Row]:
    sql = DOC_SELECT
    params: Tuple[Any,...] = ()
    if soggetto_id:
        sql += " WHERE d.soggetto_id=?"
        params = (soggetto_id,)
    sql += " ORDER BY d.data_documento DESC"
    if limit:
        sql += f" LIMIT {limit}"
    return conn.execute(sql, params).fetchall()

def fetch_subjects(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    sql = "SELECT id AS soggetto_id, codice_soggetto, ragione_sociale, tipo_soggetto FROM Soggetti ORDER BY ragione_sociale"
    return conn.execute(sql).fetchall()

def rows_to_dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(r) for r in rows]


# ---- CLIENTI ----

def fetch_clients(conn: sqlite3.Connection, only_tipo_cliente: bool=True) -> List[sqlite3.Row]:
    """Ritorna l'elenco dei clienti dalla tabella Soggetti."""
    sql = "SELECT id AS soggetto_id, codice_soggetto, ragione_sociale, tipo_soggetto, codice_fiscale, partita_iva, indirizzo, citta, telefono, email FROM Soggetti"
    if only_tipo_cliente:
        sql += " WHERE lower(tipo_soggetto)='cliente'"
    sql += " ORDER BY ragione_sociale COLLATE NOCASE"
    cur = conn.execute(sql)
    return cur.fetchall()

def get_client_by_id(conn: sqlite3.Connection, soggetto_id: int) -> Optional[sqlite3.Row]:
    sql = "SELECT * FROM Soggetti WHERE id = ?"
    cur = conn.execute(sql, (soggetto_id,))
    return cur.fetchone()

def update_client(conn: sqlite3.Connection, soggetto_id: int, data: Dict[str, Any]) -> None:
    fields = []
    values: List[Any] = []
    for k,v in data.items():
        fields.append(f"{k}=?")
        values.append(v)
    values.append(soggetto_id)
    sql = f"UPDATE Soggetti SET {', '.join(fields)} WHERE id=?"
    conn.execute(sql, values)
    conn.commit()
