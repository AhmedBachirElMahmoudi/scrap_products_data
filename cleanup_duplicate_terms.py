"""
Cleanup script to merge duplicate terms in WooCommerce attribute taxonomies.

This script identifies terms that have the same name and taxonomy but exist
as separate entries in the database, then merges them by:
1. Keeping the term with the highest count (most relationships)
2. Moving all relationships to the kept term
3. Deleting the duplicate terms
4. Recalculating term counts

Usage:
    python cleanup_duplicate_terms.py           # Dry run (show duplicates)
    python cleanup_duplicate_terms.py --fix     # Actually merge duplicates
"""

import sys
from database import connect_wp_ozar0

WP_PREFIX = "9Ew5q6v_"

def find_duplicate_terms(cursor):
    """Find all duplicate terms (same name + taxonomy)."""
    query = f"""
        SELECT 
            t.name,
            tt.taxonomy,
            COUNT(*) as duplicate_count,
            GROUP_CONCAT(tt.term_taxonomy_id ORDER BY tt.count DESC) as tt_ids,
            GROUP_CONCAT(t.term_id ORDER BY tt.count DESC) as term_ids,
            GROUP_CONCAT(tt.count ORDER BY tt.count DESC) as counts
        FROM {WP_PREFIX}terms t
        JOIN {WP_PREFIX}term_taxonomy tt ON t.term_id = tt.term_id
        WHERE tt.taxonomy LIKE 'pa_%'
        GROUP BY t.name, tt.taxonomy
        HAVING COUNT(*) > 1
        ORDER BY tt.taxonomy, t.name
    """
    
    cursor.execute(query)
    return cursor.fetchall()

def merge_duplicate_terms(cursor, conn, dry_run=True):
    """Merge duplicate terms by consolidating relationships."""
    duplicates = find_duplicate_terms(cursor)
    
    if not duplicates:
        print("No duplicate terms found!")
        return
    
    print(f"\n{'='*80}")
    print(f"Found {len(duplicates)} sets of duplicate terms")
    print(f"{'='*80}\n")
    
    total_merged = 0
    
    for dup in duplicates:
        name = dup[0]
        taxonomy = dup[1]
        dup_count = dup[2]
        tt_ids = [int(x) for x in dup[3].split(',')]
        term_ids = [int(x) for x in dup[4].split(',')]
        counts = [int(x) for x in dup[5].split(',')]
        
        # Keep the first one (highest count)
        keep_tt_id = tt_ids[0]
        keep_term_id = term_ids[0]
        remove_tt_ids = tt_ids[1:]
        remove_term_ids = term_ids[1:]
        
        print(f"--- {taxonomy}: '{name}'")
        print(f"   Duplicates: {dup_count}")
        print(f"   Counts: {counts}")
        print(f"   KEEP:   term_taxonomy_id={keep_tt_id}, count={counts[0]}")
        print(f"   REMOVE: {remove_tt_ids} (counts: {counts[1:]})")
        
        if not dry_run:
            try:
                # 1. Move all relationships from duplicates to the kept term
                for remove_tt_id in remove_tt_ids:
                    # Update relationships to point to the kept term_taxonomy_id
                    cursor.execute(f"""
                        UPDATE IGNORE {WP_PREFIX}term_relationships
                        SET term_taxonomy_id = %s
                        WHERE term_taxonomy_id = %s
                    """, (keep_tt_id, remove_tt_id))
                    moved = cursor.rowcount
                    
                    # Delete any remaining relationships (duplicates after IGNORE)
                    cursor.execute(f"""
                        DELETE FROM {WP_PREFIX}term_relationships
                        WHERE term_taxonomy_id = %s
                    """, (remove_tt_id,))
                    deleted = cursor.rowcount
                    
                    print(f"      → Moved {moved} relationships, deleted {deleted} duplicates")
                
                # 2. Update wc_product_attributes_lookup table
                for i, remove_term_id in enumerate(remove_term_ids):
                    cursor.execute(f"""
                        UPDATE IGNORE {WP_PREFIX}wc_product_attributes_lookup
                        SET term_id = %s
                        WHERE taxonomy = %s AND term_id = %s
                    """, (keep_term_id, taxonomy, remove_term_id))
                    moved_lookup = cursor.rowcount
                    
                    # Delete remaining duplicates
                    cursor.execute(f"""
                        DELETE FROM {WP_PREFIX}wc_product_attributes_lookup
                        WHERE taxonomy = %s AND term_id = %s
                    """, (taxonomy, remove_term_id))
                    deleted_lookup = cursor.rowcount
                    
                    print(f"      → Lookup: moved {moved_lookup}, deleted {deleted_lookup}")
                
                # 3. Delete the duplicate term_taxonomy entries
                for remove_tt_id in remove_tt_ids:
                    cursor.execute(f"""
                        DELETE FROM {WP_PREFIX}term_taxonomy
                        WHERE term_taxonomy_id = %s
                    """, (remove_tt_id,))
                
                # 4. Delete orphaned terms (if they're not used in other taxonomies)
                for remove_term_id in remove_term_ids:
                    # Check if this term is still used in any taxonomy
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM {WP_PREFIX}term_taxonomy
                        WHERE term_id = %s
                    """, (remove_term_id,))
                    still_used = cursor.fetchone()[0]
                    
                    if still_used == 0:
                        cursor.execute(f"""
                            DELETE FROM {WP_PREFIX}terms
                            WHERE term_id = %s
                        """, (remove_term_id,))
                        print(f"      → Deleted orphaned term {remove_term_id}")
                
                conn.commit()
                total_merged += 1
                print(f"   Merged successfully\n")
                
            except Exception as e:
                print(f"   Error merging: {e}\n")
                conn.rollback()
        else:
            print(f"   [DRY RUN - No changes made]\n")
    
    if dry_run:
        print(f"\n{'='*80}")
        print(f"DRY RUN COMPLETE - No changes were made")
        print(f"Run with --fix to actually merge duplicates")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'='*80}")
        print(f"Successfully merged {total_merged} sets of duplicates")
        print(f"{'='*80}\n")
        
        # Recalculate counts
        print("Recalculating term counts...")
        cursor.execute(f"""
            UPDATE {WP_PREFIX}term_taxonomy tt
            SET count = (
                SELECT COUNT(*)
                FROM {WP_PREFIX}term_relationships tr
                WHERE tr.term_taxonomy_id = tt.term_taxonomy_id
            )
            WHERE tt.taxonomy LIKE 'pa_%'
        """)
        conn.commit()
        print("Counts recalculated\n")

def main():
    dry_run = '--fix' not in sys.argv
    
    if dry_run:
        print("\nLOOKING FOR DUPLICATES IN DRY RUN MODE (no changes will be made)")
        print("Use --fix flag to actually merge duplicates\n")
    else:
        print("\nWARNING: RUNNING IN FIX MODE (will make changes to database)")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return
        print()
    
    conn = connect_wp_ozar0()
    cursor = conn.cursor()
    
    try:
        merge_duplicate_terms(cursor, conn, dry_run)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
