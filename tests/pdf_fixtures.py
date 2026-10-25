"""Tiny, generated PDFs with no third-party fixture-generation dependency."""


def make_pdf(text='Dataset: https://example.org/data.csv', *, annotation=None):
    escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    stream = f'BT /F1 11 Tf 40 750 Td ({escaped}) Tj ET'.encode('ascii')
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        (b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
         b'/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R '
         + (b'/Annots [6 0 R] ' if annotation else b'') + b'>>'),
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream',
    ]
    if annotation:
        uri = annotation.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        objects.append(f'<< /Type /Annot /Subtype /Link /Rect [40 730 450 765] /A << /S /URI /URI ({uri}) >> >>'.encode())
    output = bytearray(b'%PDF-1.4\n')
    positions = [0]
    for index, value in enumerate(objects, 1):
        positions.append(len(output))
        output.extend(f'{index} 0 obj\n'.encode() + value + b'\nendobj\n')
    start_xref = len(output)
    output.extend(f'xref\n0 {len(objects) + 1}\n0000000000 65535 f \n'.encode())
    for position in positions[1:]:
        output.extend(f'{position:010d} 00000 n \n'.encode())
    output.extend(f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{start_xref}\n%%EOF\n'.encode())
    return bytes(output)
