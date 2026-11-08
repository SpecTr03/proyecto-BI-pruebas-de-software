import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'

export interface DashboardPdfMetadata {
  title: string
  viewerName: string
  viewerRole: string
  activeFilters?: string[]
}

function slugify(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

export async function exportDashboardPdf(
  element: HTMLElement,
  metadata: DashboardPdfMetadata,
): Promise<void> {
  const canvas = await html2canvas(element, {
    backgroundColor: '#f5f2ea',
    scale: Math.max(2, window.devicePixelRatio || 1),
    useCORS: true,
    logging: false,
    windowWidth: Math.max(element.scrollWidth, 1100),
    onclone: (clonedDocument) => {
      clonedDocument.querySelectorAll('.pdf-exclude').forEach((node) => {
        node.remove()
      })
    },
  })

  const pdf = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
    compress: true,
  })

  const pageWidth = pdf.internal.pageSize.getWidth()
  const pageHeight = pdf.internal.pageSize.getHeight()
  const margin = 12
  const filters = metadata.activeFilters?.filter(Boolean) ?? []
  const headerHeight = filters.length > 0 ? 38 : 28
  const footerHeight = 14
  const printableWidth = pageWidth - margin * 2
  const printableHeight = pageHeight - headerHeight - footerHeight - margin
  const scale = printableWidth / canvas.width
  const sliceHeightPx = Math.floor(printableHeight / scale)

  let sourceY = 0
  let pageNumber = 1
  const generatedAt = new Date()
  while (sourceY < canvas.height) {
    if (pageNumber > 1) pdf.addPage()

    pdf.setFillColor(24, 60, 67)
    pdf.rect(0, 0, pageWidth, 18, 'F')
    pdf.setTextColor(234, 240, 230)
    pdf.setFont('helvetica', 'bold')
    pdf.setFontSize(13)
    pdf.text('SaberPro BI', margin, 11.5)
    pdf.setFont('helvetica', 'normal')
    pdf.setFontSize(8)
    pdf.text('Reporte gerencial', pageWidth - margin, 11.5, { align: 'right' })

    pdf.setTextColor(25, 51, 58)
    pdf.setFont('helvetica', 'bold')
    pdf.setFontSize(16)
    pdf.text(metadata.title, margin, 24)

    if (pageNumber === 1 && filters.length > 0) {
      pdf.setFont('helvetica', 'normal')
      pdf.setFontSize(8)
      pdf.setTextColor(112, 130, 126)
      pdf.text(`Filtros activos: ${filters.join(' · ')}`, margin, 33, {
        maxWidth: printableWidth,
      })
    }

    const sliceHeight = Math.min(sliceHeightPx, canvas.height - sourceY)
    const sliceCanvas = document.createElement('canvas')
    sliceCanvas.width = canvas.width
    sliceCanvas.height = sliceHeight
    const context = sliceCanvas.getContext('2d')

    if (!context) {
      throw new Error('No fue posible preparar la imagen del reporte.')
    }

    context.fillStyle = '#f5f2ea'
    context.fillRect(0, 0, sliceCanvas.width, sliceCanvas.height)
    context.drawImage(
      canvas,
      0,
      sourceY,
      canvas.width,
      sliceHeight,
      0,
      0,
      canvas.width,
      sliceHeight,
    )

    const imageHeight = sliceHeight * scale
    pdf.addImage(
      sliceCanvas.toDataURL('image/jpeg', 0.92),
      'JPEG',
      margin,
      headerHeight,
      printableWidth,
      imageHeight,
      undefined,
      'FAST',
    )

    sourceY += sliceHeight

    pdf.setDrawColor(223, 225, 217)
    pdf.line(margin, pageHeight - 11, pageWidth - margin, pageHeight - 11)
    pdf.setTextColor(112, 130, 126)
    pdf.setFont('helvetica', 'normal')
    pdf.setFontSize(7.5)
    const generatedLabel = generatedAt.toLocaleString('es-CO', {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
    pdf.text(
      `${metadata.viewerName} · ${metadata.viewerRole} · ${generatedLabel}`,
      margin,
      pageHeight - 7,
    )
    pdf.text(`${pageNumber}`, pageWidth - margin, pageHeight - 7, { align: 'right' })
    pageNumber += 1
  }

  const datePart = generatedAt.toISOString().slice(0, 10)
  pdf.save(`saberpro-reporte-${datePart}-${slugify(metadata.title) || 'dashboard'}.pdf`)
}
