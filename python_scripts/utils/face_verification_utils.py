import numpy as np
import math


def dist_mat(gt, det, mean=0):
	mean = np.expand_dims(mean,0)
	mat = np.zeros((det.shape[0], gt.shape[0]))
	for i in range(det.shape[0]):
		emb1 = det[i:i+1, :]
		for j in range(gt.shape[0]):
			emb2 = gt[j:j+1, :]
			dist = distance(emb1-mean, emb2-mean, distance_metric=1)
			mat[i,j] = dist
			#mat[i,j] = np.cos(dist*math.pi)
	return mat

def distance(embeddings1, embeddings2, distance_metric=0):
    if distance_metric==0:
        # Euclidian distance
        diff = np.subtract(embeddings1, embeddings2)
        dist = np.sum(np.square(diff),1)
    elif distance_metric==1:
        # Distance based on cosine similarity
        dot = np.sum(np.multiply(embeddings1, embeddings2), axis=1)
        norm = np.linalg.norm(embeddings1, axis=1) * np.linalg.norm(embeddings2, axis=1)
        similarity = dot / norm
        dist = np.arccos(similarity) / math.pi
    else:
        raise 'Undefined distance metric %d' % distance_metric 
        
    return dist


